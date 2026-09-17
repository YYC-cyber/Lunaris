"""
HermesAgent —— AI 对话核心（多轮工具调用编排）。

【职责】
- _agent_loop：最多 8 轮，LLM 返回 tool_calls 就执行工具继续，否则返回最终回复
- 记忆工具（memory_tool）：add / replace / remove，写库不影响本次快照（冻结快照）
- 实例管理：每 (user_id, soul_id) 一个实例，进程内 LRU 缓存

【设计要点】
- 冻结快照：system prompt 在 run() 开头一次性构建（含记忆），循环中 memory_tool 写库但不回改
  本次 prompt 里的记忆 → 前缀稳定，利于 LLM prefix cache。
- 工具执行用独立会话（AsyncSessionLocal），不依赖请求的 db session。
- 危机识别 / 内容安全已在 chat_service 前置拦截，本类不处理。

【说明】
- 被 services/chat_service 调用（非流式）；流式路径 run_stream 为直通透传（暂不做流式工具调用）。
"""
import json
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional

# 记忆工具 schema（OpenAI function calling 格式，中文描述）
MEMORY_TOOL_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "memory_tool",
        "description": (
            "管理关于用户的长期记忆。当用户透露了值得记住的信息（姓名/生日/偏好/习惯/"
            "重要事件/情绪状态）时用 add 新增；信息发生变化时用 replace 更新；"
            "信息不再成立时用 remove 删除。不要记忆寒暄、琐碎日常。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "replace", "remove"],
                    "description": "操作类型",
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["user_profile", "long_term", "emotional_state"],
                    "description": "记忆分类（add/replace 时用）",
                },
                "content": {
                    "type": "string",
                    "description": "新记忆内容（add 必填；replace 时为新内容）",
                },
                "old_content": {
                    "type": "string",
                    "description": "要替换/删除的旧记忆内容（replace/remove 时用）",
                },
            },
            "required": ["operation"],
        },
    },
}

# 最大工具调用轮数（防死循环）
MAX_AGENT_ITERATIONS = 8
# 实例 LRU 缓存上限
_AGENT_CACHE_MAX = 100


class HermesAgent:
    """单个 (user_id, soul_id) 的对话 agent。持身份信息，供 memory_tool 落库。"""

    def __init__(self, user_id: uuid.UUID, soul_id: int):
        self.user_id = user_id
        self.soul_id = soul_id

    # ---------------- 对外入口 ----------------
    async def run(
        self,
        llm,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """非流式完整回复（带工具调用循环）。"""
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return await self._agent_loop(llm, messages, temperature, max_tokens)

    async def run_stream(
        self,
        llm,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ):
        """流式回复（直通透传，暂不做流式工具调用）。"""
        async for delta in llm.chat_completion_stream(
            system_prompt, history, user_message, temperature, max_tokens
        ):
            yield delta

    # ---------------- 工具循环 ----------------
    async def _agent_loop(
        self,
        llm,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """多轮工具调用：LLM 有 tool_calls → 执行 → 追加结果 → 继续；否则返回最终文本。"""
        tools = [MEMORY_TOOL_SCHEMA]
        last_content = ""
        for _ in range(MAX_AGENT_ITERATIONS):
            resp = await llm.chat_completion_messages(
                messages, tools=tools, temperature=temperature, max_tokens=max_tokens
            )
            content = resp.get("content") or ""
            if content:
                last_content = content
            tool_calls = resp.get("tool_calls") or []
            if not tool_calls:
                return last_content or "（我暂时无法回答，请稍后再试）"

            # 追加 assistant 的 tool_calls
            messages.append({
                "role": "assistant",
                "content": content or None,
                "tool_calls": tool_calls,
            })
            # 逐个执行工具，追加 tool 结果
            for tc in tool_calls:
                result = await self._execute_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })
        return last_content or "（我暂时无法回答，请稍后再试）"

    async def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """执行单个工具调用，返回给 LLM 的结果字符串。"""
        fn = tool_call.get("function") or {}
        name = fn.get("name")
        if name != "memory_tool":
            return "未知工具"
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            return "工具参数不是合法 JSON"
        if not isinstance(args, dict):
            return "工具参数格式错误"

        from clients.embedding_client import get_embedding_client
        from config.database import AsyncSessionLocal
        from dao.v1_0.memory_dao import MemoryDAO

        op = args.get("operation")
        mtype = args.get("memory_type") or "user_profile"
        content = str(args.get("content") or "").strip()
        old_content = str(args.get("old_content") or "").strip()

        try:
            async with AsyncSessionLocal() as db:
                if op == "add":
                    if not content:
                        return "content 为空"
                    if await MemoryDAO.get_by_content(db, self.user_id, self.soul_id, content):
                        return "已存在，跳过"
                    vec = await get_embedding_client().embed(content)
                    await MemoryDAO.create(
                        db, user_id=self.user_id, soul_id=self.soul_id,
                        memory_type=mtype, content=content, embedding=vec,
                    )
                    await self._maybe_summarize(db)
                    return "已记住"

                if op == "replace":
                    if not content:
                        return "新内容为空"
                    if old_content:
                        await MemoryDAO.delete_by_content(db, self.user_id, self.soul_id, old_content)
                    vec = await get_embedding_client().embed(content)
                    await MemoryDAO.create(
                        db, user_id=self.user_id, soul_id=self.soul_id,
                        memory_type=mtype, content=content, embedding=vec,
                    )
                    await self._maybe_summarize(db)
                    return "已更新"

                if op == "remove":
                    target = old_content or content
                    if not target:
                        return "未指定要删除的内容"
                    deleted = await MemoryDAO.delete_by_content(db, self.user_id, self.soul_id, target)
                    return f"已删除 {deleted} 条" if deleted else "未找到匹配的记忆"

                return f"未知操作：{op}"
        except Exception as e:
            print(f"⚠️ memory_tool 执行失败: {e}")
            return f"工具执行失败：{e}"

    async def _maybe_summarize(self, db) -> None:
        """记忆条数超阈值时触发后台滚动摘要（与 core.memory 保持一致）。"""
        from core.memory import SUMMARIZE_THRESHOLD, schedule_summarize
        from dao.v1_0.memory_dao import MemoryDAO
        count = await MemoryDAO.count(db, user_id=self.user_id, soul_id=self.soul_id)
        if count > SUMMARIZE_THRESHOLD:
            schedule_summarize(self.user_id, self.soul_id)


# ---------------- 实例管理（LRU） ----------------
_agents: OrderedDict = OrderedDict()


def get_agent(user_id: uuid.UUID, soul_id: int) -> HermesAgent:
    """获取/创建 (user_id, soul_id) 的 agent 实例（LRU 淘汰）。"""
    key = (str(user_id), soul_id)
    agent = _agents.get(key)
    if agent is not None:
        _agents.move_to_end(key)
        return agent
    agent = HermesAgent(user_id, soul_id)
    _agents[key] = agent
    if len(_agents) > _AGENT_CACHE_MAX:
        _agents.popitem(last=False)  # 淘汰最久未用
    return agent
