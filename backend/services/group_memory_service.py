"""群记忆管理服务"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from dao.group_chat_dao import GroupMemoryDAO


class GroupMemoryService:
    """群记忆服务"""

    @staticmethod
    async def get_formatted_memories(
        db: AsyncSession,
        group_id: int,
        soul_id: int,
    ) -> str:
        """获取格式化的群记忆，用于 system prompt"""
        memories = await GroupMemoryDAO.get_by_group_soul(db, group_id, soul_id)

        if not memories:
            return "（这是第一次在这个群里对话，还没有特别的群记忆）"

        # 按类型分组
        memory_dict = {}
        for mem in memories:
            if mem.memory_type not in memory_dict:
                memory_dict[mem.memory_type] = []
            memory_dict[mem.memory_type].append(mem.content)

        # 格式化输出
        formatted = []
        type_labels = {
            'event': '群里发生的事件',
            'member_info': '群成员信息',
            'group_rule': '群的规则/特点',
            'topic': '群的主要话题',
        }

        for mem_type, contents in memory_dict.items():
            label = type_labels.get(mem_type, mem_type)
            formatted.append(f"\n【{label}】")
            for content in contents:
                formatted.append(f"- {content}")

        return "\n".join(formatted)

    @staticmethod
    async def extract_and_save_memories(
        db: AsyncSession,
        group_id: int,
        soul_id: int,
        ai_response: str,
        user_message: str,
        group_name: str,
    ) -> None:
        """从 AI 回复中提取群记忆并保存（可选实现，暂简化）

        这里可以用 LLM 从对话中提取关键信息作为群记忆，
        但为了简单起见，暂时不自动提取，而是依靠后续手动管理或其他触发器。
        """
        pass
