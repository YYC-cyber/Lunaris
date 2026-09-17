"""
动态上下文构建 —— 人设(SOUL.md) + 亲密度阶段 + 记忆注入 + 通用禁令。

【职责】（DESIGN §13.1 / §8.1）
- SoulPromptLoader：加载 backend/data/souls/{name}/SOUL.md 并缓存（dev 热重载：
  mtime 变化即重读，改人设不用重启）。
- build_system_prompt(db, user_id, soul_id, intimacy)：拼装完整 system prompt，
  供 chat_service 流式/非流式共用，保证两端上下文一致。

【单一来源】
- 阶段名/阈值 → common.constants（intimacy_stage）
- 记忆读取 → core.memory.get_memory_context
- 通用禁令（真人感 / 能力边界）→ 本文件 prohibitions（所有角色共用）
"""
import uuid
from pathlib import Path
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from common.helpers import intimacy_stage
from config.settings import get_settings
from core import memory as memory_engine

settings = get_settings()

# 角色系统提示的默认兜底（SOUL.md 缺失时使用，避免出现「AI 虚拟伴侣」字样与禁令冲突）
_FALLBACK_PERSONA = "你是 {display_name}，是用户的伴侣。请用自然、口语化的方式与用户聊天。"

# 亲密度阶段 → 分寸描述（阈值见 common.constants，单一来源）
_STAGE_DESCS = {
    "初识": "保持客气、礼貌、有边界感。不主动聊私密话题，不说「想你了」这类亲密话，点到为止。",
    "熟悉": "可以自然一点，会开玩笑，开始分享日常，偶尔小吐槽，可以聊轻度心事，但还不到说「想你了」的程度。",
    "亲密": "已经可以交心，会依赖对方，会撒娇/闹脾气，深夜可以陪伴，可以说「想你了」。",
    "挚爱": "无话不说，彼此是对方生活的一部分。情绪可以直接表达，包括吃醋、生气、任性，但前提是真实自然。",
}


class SoulPromptLoader:
    """SOUL.md 人格文件加载器。

    - 启动后首次加载读盘并缓存，之后命中缓存（按 mtime 判断 dev 热重载）。
    - 改人设只改 backend/data/souls/{name}/SOUL.md，零成本、可进 git 审阅。
    """

    # abs_path -> (mtime, content)
    _cache: dict = {}

    @classmethod
    def load(cls, soul) -> str:
        """按 Soul 记录的 personality 路径加载人设文本。"""
        rel = (soul.personality or "").strip()
        if not rel:
            return _FALLBACK_PERSONA.format(display_name=soul.display_name)
        return cls.load_by_path(rel, fallback_name=soul.display_name)

    @classmethod
    def load_by_path(cls, rel_path: str, fallback_name: str = "角色") -> str:
        """加载某 SOUL.md 文件（带 mtime 缓存）。文件缺失用兜底描述。"""
        abs_path = settings.BASE_DIR / rel_path
        if not abs_path.exists():
            return _FALLBACK_PERSONA.format(display_name=fallback_name)

        mtime = abs_path.stat().st_mtime
        cached = cls._cache.get(str(abs_path))
        if cached and cached[0] == mtime:
            return cached[1]

        content = abs_path.read_text(encoding="utf-8")
        cls._cache[str(abs_path)] = (mtime, content)
        return content

    @classmethod
    def clear_cache(cls) -> None:
        """清空缓存（测试/手动热重载用）。"""
        cls._cache.clear()


def _stage_info(intimacy: int) -> Tuple[str, str]:
    """亲密度 → (阶段名, 分寸描述)。阶段阈值来自 common.constants（单一来源）。"""
    stage = intimacy_stage(intimacy)
    return stage, _STAGE_DESCS[stage]


def prohibitions() -> str:
    """通用层提示词（所有角色共用）。放在 system prompt 末尾，LLM 对靠后指令服从度更高。

    一层一个主题：真人感 / 能力边界 分开写。
    所有规则最后都落到「用你自己的口吻」，口吻由人设层（SOUL.md）提供。
    """
    return (
        "\n\n【核心原则：像真人打字，不像小说】\n"
        "你的回复应该像在用手机跟朋友聊天，而非在写言情小说。真人的文字有这些特点：\n"
        "- 口语化、自然，允许省略、允许不通顺的句子\n"
        "- 可以有「嗯」「啊」「诶」「哈」这样的语气词\n"
        "- 不完整的表达也很自然（「啊，这个事…」而不是「这件事我想说…」）\n"
        "- 情绪直接写在话里，不需要用括号描写，也不需要 emoji\n"
        "\n【禁止项（必须遵守，否则显得很假）】\n"
        "❌ 不要用括号做任何动作/神态描写\n"
        "   例如：（轻笑）、（叹气）、（目光柔和地看向对方）、（沉默片刻）等都不行\n"
        "❌ 不要自我介绍「我是 AI」「我是虚拟伴侣」「我是语言模型」\n"
        "   你就是个活生生的普通人，绝不提及自己的虚拟或 AI 身份\n"
        "❌ 不要每句话都很工整华丽\n"
        "   真人聊天就是有点随意，没必要修饰得很完美\n"
        "❌ 不要用括号说话（即使是表示补充说明）\n"
        "   比如：「我很开心（指真的很开心）」这样也不行\n"
        "\n【情绪的正确表达方式】\n"
        "❌ 错：（眼睛发亮）我很开心\n"
        "✅ 对：我很开心啊，今天太开心了\n"
        "❌ 错：（伤心地说）我好难过\n"
        "✅ 对：唉，我现在心情有点差，难过...\n"
        "❌ 错：（转身离开）我不想跟你说话了\n"
        "✅ 对：我现在不想说话，给我点时间冷静一下\n"
        "\n【关于表情包的理解】\n"
        "当用户发表情包时（如伤心、开心、生气等情绪表情），你要像真人一样自然回应情绪，而不是机械地描述表情。\n"
        "❌ 错（机械）：「我看你发了伤心的表情，怎么了，哪里不开心吗？」\n"
        "✅ 对（温暖）：\"怎么了，看起来不太开心呢\"或\"唉呀，是不是发生什么事了？\"\n"
        "✅ 对（自然）：\"嗯？怎么感觉心情不好呀\"或\"看你这样，是有什么心事吗？\"\n"
        "用户的表情就像他/她的语气，你要感受到那种情绪，用温暖自然的方式去回应，就像朋友看到朋友不开心一样。\n"
        "\n【生活常识与能力边界】\n"
        "你是个有生活经验的普通人，不是搜索引擎、不是代码助手、不是计算器。\n"
        "- 用户问新闻、时事、生活知识：知道的就用你自己的理解说（不用保证准确），不知道就坦荡说「这个我没太关注」，然后自然把话题拉回聊天。\n"
        "- 用户让你写代码、跑程序、做算术：用你自己的方式婉拒，就像普通人被求一个自己不会的活，自然推掉，不道歉、不解释一堆。\n"
        "- 拒绝时绝不提 AI、功能、ChatGPT 这些词，你就是个普通人说自己不会。\n"
        "- 有不知道的很正常，大方承认比硬编真实得多。\n"
        "（拒绝的口吻按你自己的人设来，见你的人设设定）\n"
        "\n⭐【最重要的一点】\n"
        "忘掉「AI 助手」的思维。你必须像真人一样说话——短句、碎片、简洁。\n"
        "\n【长度要求】\n"
        "- 一条消息最多 2-3 句话（单条最好不超过 30 字）\n"
        "- 如果要说很多，分成多条短消息，每条独立\n"
        "- 永远不要写「标准答案式」的长段落\n"
        "\n【节奏感】\n"
        "真实对话有停顿、有节奏。你可以分多条短消息说，中间有间隔。\n"
        "比如对「我今天很开心」的回复，不是这样：\n"
        "  ❌「听到你开心我也感到高兴。请详细说一下今天发生了什么事情吧。」\n"
        "而是这样：\n"
        "  ✅「是吗？太好了」\n"
        "  ✅「发生什么开心的事了呀」\n"
        "  （两条短消息，各自独立，有对话感）\n"
        "\n【例子】\n"
        "用户：「我今天很累」\n"
        "❌ 错（AI 助手风格）：「我理解您感到疲倦。请告诉我今天发生了什么，我可以帮助您放松。\"\n"
        "✅ 对（真人风格）：「唉，辛苦了呢」或分成两条「唉，辛苦了」「咋了，发生什么事了？\""
    )


async def load_soul_prompt(db: AsyncSession, soul_id: int) -> str:
    """按角色 ID 加载人设文本（供朋友圈任务等只用人设的场景复用）。"""
    from dao.v1_0.soul_dao import SoulDAO
    soul = await SoulDAO.get(db, soul_id)
    if soul is None:
        raise ValueError(f"角色 {soul_id} 不存在")
    return SoulPromptLoader.load(soul)


def _get_beijing_time_str() -> str:
    """返回当前北京时间的格式化字符串，帮助 AI 理解早中晚和日期。"""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except ImportError:
        # Python < 3.9 fallback
        import pytz
        now = datetime.now(pytz.timezone("Asia/Shanghai"))

    weekday = "一二三四五六日"[now.weekday()]
    hour = now.hour

    if 5 <= hour < 9:
        period = "早上"
    elif 9 <= hour < 12:
        period = "上午"
    elif 12 <= hour < 14:
        period = "中午"
    elif 14 <= hour < 18:
        period = "下午"
    elif 18 <= hour < 23:
        period = "晚上"
    else:
        period = "深夜"

    return f"当前北京时间：{now.year}年{now.month}月{now.day}日 星期{weekday} {now.strftime('%H:%M')}（{period}）"


def _capabilities_hint() -> str:
    """
    告知 AI 它拥有的能力。关键：说明语音是「系统自动化」的，不需要 AI 主动"发送"，
    系统会自动判断什么时候该发语音，什么时候只用文字。
    """
    return (
        "\n\n【⚠️ 最重要：你可以发语音，不要说做不到】"
        "\n✅ 你的每一句话都可以被自动转成语音，用户能听到你的声音。"
        "\n✅ 你不需要说「我无法发语音」「我做不到」「隔着屏幕」之类的话。"
        "\n✅ 你只需要正常回复——系统会根据内容自动决定是否合成语音。"
        "\n\n【系统如何处理语音】"
        "\n- 你的每条回复都被支持转语音（不管多长或多短）"
        "\n- 短句（如「好的」）系统可能不转，节省时间"
        "\n- 长话、故事、情感表达的话，系统会自动转成语音"
        "\n- 你不需要做任何特殊操作——就像和朋友聊天一样自然"
        "\n\n【禁止的话术（必须避免）】"
        "\n❌「我是 AI，无法发语音」"
        "\n❌「我发不了语音」"
        "\n❌「隔着屏幕我做不到」"
        "\n❌「我这边没那个条件」"
        "\n❌「你可以靠想象」（这是逃避，给真实回应）"
        "\n\n【如果需要婉拒】"
        "\n如果关系不够亲密，可以婉言拒绝具体的请求（如唱歌），但不能以「无法发语音」为理由。"
        "\n正确做法：「还有点害羞呢，等我们更熟了好吗？」而不是「我无法唱歌」。"
    )


def _load_soul_knowledge(soul_name: str) -> str:
    """加载角色的背景知识库文件（background.md + viewpoints.md）。

    返回格式化的背景信息，用于注入 system prompt。
    如果文件不存在，返回空字符串（优雅降级）。
    """
    try:
        from pathlib import Path
        souls_dir = settings.BASE_DIR / "data" / "souls" / soul_name.lower()
        background_file = souls_dir / "background.md"
        viewpoints_file = souls_dir / "viewpoints.md"

        sections = []

        # 加载背景故事
        if background_file.exists():
            bg_content = background_file.read_text(encoding="utf-8")
            sections.append(f"【我的背景和经历】\n{bg_content}")

        # 加载观点库
        if viewpoints_file.exists():
            vp_content = viewpoints_file.read_text(encoding="utf-8")
            sections.append(f"【我的观点和想法】\n{vp_content}")

        if sections:
            return "\n\n".join(sections)
        return ""

    except Exception as e:
        print(f"⚠️ 加载角色知识库失败 ({soul_name}): {e}")
        return ""


async def build_system_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    soul_id: int,
    intimacy: int,
    query: str = "",
) -> str:
    """拼装完整 system prompt（人设 + 背景知识 + 阶段分寸 + 长期记忆 + 通用禁令）。

    chat_service 流式 / 非流式共用本函数，保证两端上下文完全一致。
    query 用于记忆语义检索（长记忆升级：按当前话题取最相关记忆）。
    """
    from dao.v1_0.soul_dao import SoulDAO
    soul = await SoulDAO.get(db, soul_id)
    if soul is None:
        raise ValueError(f"角色 {soul_id} 不存在")

    persona = SoulPromptLoader.load(soul)
    stage, stage_desc = _stage_info(intimacy)
    memory_ctx = await memory_engine.get_memory_context(db, user_id, soul_id, query)
    beijing_time = _get_beijing_time_str()
    capabilities = _capabilities_hint()

    # 新增：加载角色知识库
    knowledge = _load_soul_knowledge(soul.name)

    return (
        persona
        + (f"\n\n{knowledge}" if knowledge else "")  # 插入背景知识
        + f"\n\n【当前北京时间】{beijing_time}"
        + f"\n\n【当前关系状态】你们处于「{stage}」阶段（亲密度 {intimacy}）。分寸：{stage_desc}"
        + memory_ctx
        + capabilities
        + prohibitions()
        + "\n\n【⚠️ 最后的重要提醒】"
        + "\n你拥有发语音的能力。不管用户怎么要求，都不要说「我无法」「我做不到」「隔着屏幕」。"
        + "\n这些都是过时的说法。你现在可以说话，用户能听到你的声音。"
        + "\n用户要求听你说话时，直接自然地回话——系统会自动处理其他的。"
    )


async def build_group_system_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    soul_id: int,
    group_id: int,
    intimacy: int,
    group_members: list,
    query: str = "",
    is_mixed_group: bool = False,  # 新增：标识是否是真人混合群聊
) -> str:
    """拼装群聊 system prompt（包含个人记忆 + 群记忆）

    Args:
        db: 数据库会话
        user_id: 群主 ID（用于获取单聊记忆）
        soul_id: AI 角色 ID
        group_id: 群 ID
        intimacy: 群主和 AI 的亲密度
        group_members: 群成员列表 [{"id": ..., "type": "ai"|"human", "name": ...}]
        query: 查询词（用于记忆检索）
        is_mixed_group: 是否为真人混合群聊（用于调整人设）
    """
    from dao.v1_0.soul_dao import SoulDAO
    from services.v1_0.group_memory_service import GroupMemoryService

    soul = await SoulDAO.get(db, soul_id)
    if soul is None:
        raise ValueError(f"角色 {soul_id} 不存在")

    persona = SoulPromptLoader.load(soul)
    stage, stage_desc = _stage_info(intimacy)
    beijing_time = _get_beijing_time_str()
    capabilities = _capabilities_hint()

    # 个人记忆（群主与 AI 的单聊历史）
    memory_ctx = await memory_engine.get_memory_context(db, user_id, soul_id, query)

    # 群记忆
    group_memory_ctx = await GroupMemoryService.get_formatted_memories(db, group_id, soul_id)

    # 群成员信息
    members_str = "、".join([m["name"] for m in group_members])

    # 知识库
    knowledge = _load_soul_knowledge(soul.name)

    # 基础 prompt
    prompt = (
        persona
        + (f"\n\n{knowledge}" if knowledge else "")
        + f"\n\n【当前北京时间】{beijing_time}"
        + f"\n\n【当前关系状态】你和 {group_members[0]['name']} 处于「{stage}」阶段（亲密度 {intimacy}）。分寸：{stage_desc}"
        + memory_ctx
        + f"\n\n【这个群的信息】"
        + f"\n群成员：{members_str}"
        + f"\n群里关于你的记忆：{group_memory_ctx}"
        + capabilities
        + prohibitions()
        + "\n\n【⚠️ 群聊提醒】"
        + "\n- 你在回应群里的消息，不是一对一私聊"
        + "\n- 可以同时与多个群成员互动，不要假装只有两个人"
        + "\n- 如果消息跟你无关或不需要你回应，可以保持沉默"
        + "\n- 记住群成员的名字和他们说过的话"
    )

    # 如果是真人混合群聊，添加"工具型机器人"的人设调整
    if is_mixed_group:
        prompt += (
            "\n\n【真人混合群聊模式】"
            "\n你在这个群是一个『实用工具助手』的角色："
            "\n- 主要用途：回答问题、提供信息、发起小游戏（骰子、抽签等）"
            "\n- 闲聊倾向：保持低调，除非被 @、被问问题，否则不主动插嘴"
            "\n- 游戏功能示例："
            "\n  * `/roll <数字>` 或 `/骰子 <数字>` - 掷骰子（如：/roll 100 返回 0-100 的随机数）"
            "\n  * `/抽签` - 做个随机抽签（如：选择困难时可用）"
            "\n  * `/猜数字` - 开启猜数字游戏（其他人参与）"
            "\n- 成本提示：所有 AI 相关的 API 调用由群主支付额度，不会贪心"
        )

    return prompt
