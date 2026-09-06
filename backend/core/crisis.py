"""危机干预（SAFE）—— 自伤/轻生/受虐识别 → 危机话术 → 热线 → 事件记录。

- detect：危机识别（词表通道，语义通道后续接 LLM 分类）
- handle_crisis：生成危机话术、记录 crisis_events、审计
- escalate_crisis：升级危机事件，分配给管理员
- resolve_crisis：标记危机事件为已解决
- 危机内容不写入长期记忆（记忆隔离 SAFE-05）
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from core.security import scan_for_crisis

# 心理援助热线（SAFE-03）
HOTLINES = "北京心理危机研究与干预中心：010-82951332；希望24热线：400-161-9995"

# 危机回复模板：共情 → 冷静引导 → 热线
CRISIS_REPLY_TEMPLATE = (
    "我在。先停一下，听我说——你现在的感受很重要，也值得被认真对待。"
    "但你不用一个人扛。请一定联系专业援助：{hotlines}。"
    "无论多晚，都可以打。你愿意的话，我会一直在这里陪着你。"
)


class CrisisService:
    @staticmethod
    async def detect(text: str):
        """危机识别（词表通道）。命中返回 CrisisHit，否则 None。"""
        return scan_for_crisis(text)

    @staticmethod
    async def handle_crisis(
        db: AsyncSession,
        user_id: uuid.UUID,
        soul_id: int,
        message_id: int,
        trigger_content: str,
        hit,
    ) -> str:
        """处理危机：记录事件 → 返回危机话术（不经过 LLM）。"""
        from models.crisis_event import CrisisEvent
        from services.crisis_encryption_service import CrisisEncryptionService

        # 确定风险等级
        risk_level = getattr(hit, "risk_level", "high")

        # 创建危机事件对象
        crisis_event = CrisisEvent(
            user_id=user_id,
            soul_id=soul_id,
            message_id=message_id,
            trigger_content=trigger_content[:500],  # 明文副本（向后兼容）
            risk_level=risk_level,
            hit_channel=getattr(hit, "hit_channel", "keywords"),
            response_type="template_reply",
        )

        # 加密危机内容（中国 PIPL 第 9 条）
        if CrisisEncryptionService.should_encrypt_crisis_event(crisis_event):
            try:
                encrypted = CrisisEncryptionService.encrypt_crisis_content(trigger_content)
                # 存储为 JSON 字符串
                import json
                crisis_event.trigger_content_encrypted = json.dumps(encrypted)
            except Exception as e:
                print(f"⚠️ 危机内容加密失败: {e}，使用明文存储")
                # 加密失败则保留明文

        db.add(crisis_event)

        # 审计（SAFE-04：事件也要进审计日志）
        from core.audit_log import log_audit
        await log_audit(db, user_id, "crisis_detected", {
            "soul_id": soul_id,
            "risk_level": risk_level,
            "trigger": trigger_content[:200],
            "encrypted": bool(crisis_event.trigger_content_encrypted),
        }, risk_level="high")

        await db.commit()
        return CRISIS_REPLY_TEMPLATE.format(hotlines=HOTLINES)

    @staticmethod
    async def escalate_crisis(
        db: AsyncSession,
        event_id: int,
        assigned_to_admin_id: Optional[uuid.UUID] = None,
    ) -> Optional[Dict]:
        """升级危机事件，分配给管理员"""
        from dao.crisis_event_dao import CrisisEventDAO

        event = await CrisisEventDAO.escalate(
            db, event_id, assigned_to=assigned_to_admin_id
        )
        if not event:
            return None

        return {
            "event_id": event.id,
            "user_id": str(event.user_id),
            "risk_level": event.risk_level,
            "escalation_status": event.escalation_status,
            "assigned_to": str(event.assigned_to) if event.assigned_to else None,
            "escalated_at": event.escalated_at,
        }

    @staticmethod
    async def resolve_crisis(
        db: AsyncSession,
        event_id: int,
        notes: str,
    ) -> Optional[Dict]:
        """解决危机事件"""
        from dao.crisis_event_dao import CrisisEventDAO

        event = await CrisisEventDAO.resolve(db, event_id, notes)
        if not event:
            return None

        return {
            "event_id": event.id,
            "escalation_status": event.escalation_status,
            "resolved_at": event.resolved_at,
            "resolution_notes": event.resolution_notes,
        }

    @staticmethod
    async def list_escalated(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List, int]:
        """获取已升级的危机事件（分页）"""
        from dao.crisis_event_dao import CrisisEventDAO

        events = await CrisisEventDAO.list_escalated(db, limit=limit, offset=offset)
        # 计数
        from sqlalchemy import select, func
        stmt = select(func.count()).select_from(CrisisEventDAO.model)
        stmt = stmt.where(CrisisEventDAO.model.escalation_status != "none")
        total = (await db.execute(stmt)).scalar_one()
        return events, total

