# backend/core/memory.py
"""记忆引擎（规划中；当前记忆读写实现在 services/chat_service.py）。

【计划内容】
- extract_important_info：从对话提取关键信息
- classify / save_memories / summarize（>50 条压缩）/ inject_memories
- 冻结快照机制（会话开始注入，会话中写入不影响前缀，保持 LLM prefix cache）
"""

# backend/core/memory.py
"""
记忆引擎 —— 从对话中提取、安全扫描、去重落库

【职责】
- 从用户消息 + AI 回复中提取关于用户的重要信息
- 安全扫描（防注入/防外泄）
- 按类型分类去重，写入 memory_records 表
- 后台任务调度（不阻塞主流程）

【调用链】
chat_service → memory.extract_and_save（后台任务）
"""

import asyncio
import json
import re
from typing import List, Dict, Any
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants import MEMORY_TYPES
from config.database import AsyncSessionLocal
from core.security import scan_memory_content
from dao.v1_0.memory_dao import MemoryDAO
from services.api_config_service import ApiConfigService
from clients.llm_client import LLMClient
from clients.embedding_client import EMBEDDING_DIM, get_embedding_client

# 记忆表存在性缓存
_memory_table_ok: bool | None = None
# 持有后台记忆任务引用，防止被垃圾回收
_memory_tasks: set = set()

# 滚动摘要：记忆条数超过阈值 → 后台压缩到目标条数（防止上下文爆掉）
SUMMARIZE_THRESHOLD = 50
SUMMARIZE_TARGET = 20


async def _check_memory_table_exists(db: AsyncSession) -> bool:
    """检查 memory_records 表是否存在（用 to_regclass，不抛错）"""
    global _memory_table_ok
    if _memory_table_ok is None:
        _memory_table_ok = (
            (await db.execute(text("SELECT to_regclass('memory_records')"))).scalar()
            is not None
        )
    return _memory_table_ok


async def _make_llm(db: AsyncSession, user_id: uuid.UUID):
    """按用户 API 配置创建 LLM 客户端（复用 chat_service 的逻辑）"""
    cfg = await ApiConfigService.resolve(db, user_id, "llm")
    if not cfg.get("api_key"):
        return None
    return LLMClient(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        model=cfg.get("model"),
    )


async def extract_candidates(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_content: str,
    ai_content: str,
) -> List[Dict[str, str]]:
    """
    调用 LLM 从对话中提取【关于用户】的记忆点
    失败返回空列表
    """
    prompt = (
        "你是记忆提取器。从下面的对话中提取【关于用户】的重要信息，用于 AI 伴侣的长期记忆。\n"
        "只提取关于用户本人的，AI 说的话忽略。\n"
        "分类：\n"
        "- user_profile：姓名、生日、偏好、习惯、身份等稳定信息\n"
        "- long_term：重要事件、决定、人生大事\n"
        "- emotional_state：情绪状态或事件（如最近失恋了、工作压力大）\n"
        "不要提取：寒暄、琐碎日常、AI 自己的观点。\n"
        "严格输出 JSON 数组，例如 [{\"type\":\"user_profile\",\"content\":\"用户叫小明，喜欢喝奶茶\"}]，不要输出任何其它文字。"
    )
    conversation = f"用户：{user_content}\nAI：{ai_content}"
    llm = await _make_llm(db, user_id)
    if llm is None:
        return []

    try:
        raw = await llm.chat_completion(
            system_prompt=prompt,
            history=[],
            user_message=conversation,
            temperature=0.3,
            max_tokens=500,
        )
        return parse_json(raw)
    except Exception as e:
        print(f"⚠️ 记忆提取 LLM 调用失败: {e}")
        return []


def parse_json(raw: str) -> List[Dict[str, str]]:
    """从 LLM 输出中稳健解析记忆 JSON 数组（容忍 ```json 包裹和前后杂音）。"""
    if not raw:
        return []
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    valid_types = set(MEMORY_TYPES)
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        content = str(item.get("content") or "").strip()
        if t in valid_types and content and len(content) <= 200:
            result.append({"type": t, "content": content})
    return result


async def extract_and_save(
    user_id: uuid.UUID,
    soul_id: int,
    user_content: str,
    ai_content: str,
) -> None:
    """
    后台任务：提取 → 安全扫描 → 落库
    任何失败都不影响主流程，使用独立 DB 会话
    """
    try:
        async with AsyncSessionLocal() as db:
            # 检查表是否存在
            if not await _check_memory_table_exists(db):
                return

            candidates = await extract_candidates(db, user_id, user_content, ai_content)
            # 安全扫描：命中注入/外泄模式的候选直接丢弃
            safe = [c for c in candidates if scan_memory_content(c["content"]).is_passed]
            if not safe:
                return

            emb_client = get_embedding_client()
            saved = 0
            for c in safe:
                exists = await MemoryDAO.get_by_content(db, user_id, soul_id, c["content"])
                if exists:
                    continue
                vec = await emb_client.embed(c["content"])  # 语义检索用向量
                await MemoryDAO.create(
                    db,
                    user_id=user_id,
                    soul_id=soul_id,
                    memory_type=c["type"],
                    content=c["content"],
                    embedding=vec,
                )
                saved += 1
            if saved:
                print(f"✅ 记忆已保存 {saved} 条")
                # 滚动摘要：条数超阈值则后台压缩
                count = await MemoryDAO.count(db, user_id=user_id, soul_id=soul_id)
                if count > SUMMARIZE_THRESHOLD:
                    schedule_summarize(user_id, soul_id)
    except Exception as e:
        print(f"⚠️ 记忆保存失败: {e}")


def schedule_extraction(
    user_id: uuid.UUID,
    soul_id: int,
    user_content: str,
    ai_content: str,
) -> None:
    """
    排队后台记忆提取任务（持有引用防 GC）
    供 chat_service 调用
    """
    task = asyncio.create_task(
        extract_and_save(user_id, soul_id, user_content, ai_content)
    )
    _memory_tasks.add(task)
    task.add_done_callback(_memory_tasks.discard)


async def get_memory_context(
    db: AsyncSession, user_id: uuid.UUID, soul_id: int, query: str = None
) -> str:
    """读取长期记忆注入 prompt（读取端，供 context_service / chat_service 调用）。

    长记忆升级：传 query 时按语义检索（pgvector 余弦相似度）最相关的记忆；
    未传 query 或语义检索无结果时，回退为最近 10 条。
    表未建（未跑迁移）时直接返回空，避免对缺失表的查询污染会话。
    """
    if not await _check_memory_table_exists(db):
        return ""
    if query and query.strip():
        vec = await get_embedding_client().embed(query)
        records = await MemoryDAO.list_similar(db, user_id, soul_id, vec, 10)
        if not records:
            records = await MemoryDAO.list_by_user_soul(db, user_id, soul_id, 10)
    else:
        records = await MemoryDAO.list_by_user_soul(db, user_id, soul_id, 10)
    if not records:
        return ""
    lines = [f"- {r.content}" for r in records]
    return "\n\n【关于用户的记忆】\n" + "\n".join(lines)


def schedule_summarize(user_id: uuid.UUID, soul_id: int) -> None:
    """排队后台记忆压缩任务（持有引用防 GC）。"""
    task = asyncio.create_task(summarize(user_id, soul_id))
    _memory_tasks.add(task)
    task.add_done_callback(_memory_tasks.discard)


async def summarize(user_id: uuid.UUID, soul_id: int) -> None:
    """滚动摘要：把某用户+角色的记忆压缩到 SUMMARIZE_TARGET 条（合并去重、删琐碎）。"""
    try:
        async with AsyncSessionLocal() as db:
            count = await MemoryDAO.count(db, user_id=user_id, soul_id=soul_id)
            if count <= SUMMARIZE_THRESHOLD:
                return
            records = await MemoryDAO.list_by_user_soul(db, user_id, soul_id, limit=500)
            llm = await _make_llm(db, user_id)
            if llm is None:
                return

            existing = "\n".join(f"- [{r.memory_type}] {r.content}" for r in records)
            prompt = (
                f"你是记忆压缩器。下面是 AI 伴侣记住的关于用户的 {len(records)} 条信息，数量过多。\n"
                f"请把它们压缩合并成不超过 {SUMMARIZE_TARGET} 条：保留重要、稳定、有区分度的信息，"
                "合并重复或相近的条目，删除琐碎、过期、无意义的内容。\n"
                "分类沿用 user_profile / long_term / emotional_state。\n"
                "严格输出 JSON 数组，例如 [{\"type\":\"user_profile\",\"content\":\"...\"}]，不要输出任何其它文字。\n\n"
                f"【当前记忆】\n{existing}"
            )
            raw = await llm.chat_completion(
                system_prompt="你是记忆压缩器，只输出 JSON。",
                history=[], user_message=prompt, temperature=0.3, max_tokens=1500,
            )
            items = parse_json(raw)
            if not items:
                return

            await MemoryDAO.delete_by_user_soul(db, user_id, soul_id)
            emb_client = get_embedding_client()
            for it in items:
                vec = await emb_client.embed(it["content"])
                await MemoryDAO.create(
                    db, user_id=user_id, soul_id=soul_id,
                    memory_type=it["type"], content=it["content"], embedding=vec,
                )
            print(f"✅ 记忆已压缩：{count} → {len(items)} 条")
    except Exception as e:
        print(f"⚠️ 记忆压缩失败: {e}")
