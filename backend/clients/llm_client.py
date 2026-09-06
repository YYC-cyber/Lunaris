"""
LLM 客户端（DeepSeek）—— 框架占位，按注释实现。

【方法】
- chat_completion(messages, temperature=0.7) -> ChatCompletion
  # 非流式；OpenAI 兼容格式
- chat_completion_stream(messages) -> AsyncIterator[Delta]
  # 流式；逐块 yield delta.content
  # 同时解析 tool_calls（多轮工具调用需要）
- embedding(text) -> list[float]        # 兼容接口说明；当前由长期记忆模块使用

【配置】settings.DEEPSEEK_API_KEY / BASE_URL / MODEL

【说明】
- 所有外部调用失败自动重试 3 次（指数退避）
- 超时：首字 10s / 单次 60s，避免长回复卡死
"""
import json

# backend/clients/llm_client.py
"""
DeepSeek API 客户端 —— 非流式调用

【职责】
- 封装 HTTP 请求到 DeepSeek 的 /v1/chat/completions
- 支持 system prompt + 历史消息 + 当前用户消息
- 返回 AI 回复文本

【配置】
从 settings 读取 DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
"""

import asyncio
import httpx
from typing import Any, List, Dict, Optional, AsyncGenerator

from config.settings import get_settings

settings = get_settings()


def friendly_llm_error(e: Exception, model: str = "") -> str:
    """把 LLM 调用异常转成用户可读的中文提示（供聊天兜底 / 测试连接用）。

    :param e: 异常（常见为 httpx.HTTPStatusError / TimeoutException）
    :param model: 当前使用的模型名（便于提示）
    """
    status = getattr(getattr(e, "response", None), "status_code", None)
    body = ""
    try:
        body = str(getattr(getattr(e, "response", None), "text", "") or e)
    except Exception:
        body = str(e)
    low = body.lower()

    if status in (401, 403) or "unauthorized" in low or "invalid api key" in low or "authentication" in low:
        return "API Key 无效或已过期，请在「我 → API 配置」检查"
    if status == 400 or "model_not_found" in low or "model" in low:
        return f"模型名可能不正确（当前：{model or '未填'}），请在「我 → API 配置」核对模型名"
    if status == 404 or "not found" in low:
        return "接口地址(base_url)可能有误，请检查"
    if status == 429 or "rate limit" in low or "quota" in low:
        return "请求太频繁或额度不足，请稍后再试"
    if isinstance(e, (httpx.TimeoutException, asyncio.TimeoutError)) or "timeout" in low:
        return "连接超时，请检查 base_url 或网络"
    return (str(e) or "未知错误")[:120]


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """可传入用户自带的 API 配置（BYOK）；未传入则回退全局 settings。"""
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = model or settings.DEEPSEEK_MODEL
        self.timeout = 30.0

    async def call_once(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 50,
    ) -> str:
        """快速单次调用（用于简单判断）。

        :param prompt: 完整 prompt（已包含 system + 内容）
        :param temperature: 低温度确保一致性
        :param max_tokens: 短回复
        """
        messages = [{"role": "user", "content": prompt}]

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_completion(
        self,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """
        调用 DeepSeek API 生成回复

        :param system_prompt: 系统人设
        :param history: 对话历史 [{"role": "user"|"assistant", "content": "..."}]
        :param user_message: 当前用户输入
        :param temperature: 随机性
        :param max_tokens: 最大输出长度
        """
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # 添加历史（只取最近的，防止上下文超长）
        for msg in history:
            messages.append(msg)
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,  # 非流式
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # 提取回复内容
            return data["choices"][0]["message"]["content"]

    async def chat_completion_messages(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[dict]] = None,
        temperature: float = 0.8,
        max_tokens: int = 300,  # 降低到 300：短回复
    ) -> Dict[str, Any]:
        """非流式调用，接受完整 messages 列表，支持工具调用（function calling）。

        :return: {"content": str, "tool_calls": list}
        tool_calls 为 OpenAI 兼容格式 [{"id","type":"function","function":{"name","arguments"}}]。
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            return {
                "content": message.get("content") or "",
                "tool_calls": message.get("tool_calls") or [],
            }

    # =======  流式输出 =======
    async def chat_completion_stream(
        self,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 300,  # 降低到 300：短回复
    ) -> AsyncGenerator[str,None]:
        """流式调用 DeepSeek API, 逐块返回生成的文本"""
        messages =[
            {"role": "system", "content": system_prompt}
        ]
        for msg in history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        url = f"{self.base_url}/chat/completions"
        headers ={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload={
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async  with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:] # 去掉 "data: " 前缀
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            content = delta["content"]
                            if content:
                                yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
