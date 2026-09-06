# backend/common/helpers.py
"""通用工具函数。"""
import time
import uuid

from common.constants import INTIMACY_STAGE_NAMES, INTIMACY_STAGE_THRESHOLDS


def now_ts() -> int:
    """当前秒级 Unix 时间戳。"""
    return int(time.time())


def gen_uuid() -> str:
    """生成 UUID 字符串。"""
    return str(uuid.uuid4())


def intimacy_stage(intimacy: int) -> str:
    """亲密度 → 阶段名。

    阈值来自 constants.INTIMACY_STAGE_THRESHOLDS（单一来源，避免各处重复写 25/50/75）。
    """
    for i, threshold in enumerate(INTIMACY_STAGE_THRESHOLDS):
        if intimacy < threshold:
            return INTIMACY_STAGE_NAMES[i]
    return INTIMACY_STAGE_NAMES[-1]


def opposite_gender(gender: str) -> str:
    """返回异性（男→女，女→男）。"""
    return "female" if gender == "male" else "male"


def remaining_days(expiry) -> int | None:
    """剩余可用天数（无到期时间返回 None，已到期返回 0）。"""
    if not expiry:
        return None
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC，与列一致
    delta = expiry - now
    return max(delta.days, 0)


# 情绪关键词表（供 extract_emotion 用）
_EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "哈哈", "太好了", "棒", "喜欢", "好耶", "太棒", "笑", "开心呀", "开心极了"],
    "sad": ["难过", "伤心", "委屈", "失落", "想哭", "累了", "辛苦", "压力", "烦", "难受", "孤独", "疲惫"],
    "angry": ["生气", "愤怒", "气死", "恼火", "可恶", "讨厌", "烦死了", "火大"],
    "gentle": ["想你了", "别怕", "陪着你", "抱抱", "放心", "没事的", "我在", "别担心", "有我"],
}


def extract_emotion(text: str) -> str:
    """从文本提取情绪（关键词启发式），供 TTS 情绪路由。"""
    if not text:
        return "neutral"
    scores = {emo: sum(1 for w in words if w in text) for emo, words in _EMOTION_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"
