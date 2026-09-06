# backend/clients/tts_client.py
"""Edge TTS 情绪路由 —— 免费、免 key。

【情绪 → 音色 + 语速】（参考 astrbot_plugin_tts_emotion_router 的思路，换成免 key 的 Edge TTS）
- happy   → 晓伊（女·轻快）   +20%
- sad     → 云希（男·温柔）   -10%
- angry   → 云健（男·有力）   +30%
- gentle  → 晓晓（女·温柔）   -5%
- neutral → 晓晓（女·默认）   +0%

【用法】
    client = TTSClient()
    url = await client.synthesize("你好呀", emotion="happy")
"""
import re
import uuid
from pathlib import Path

from config.settings import get_settings

settings = get_settings()

# 输出目录（由 main.py 静态挂载为 /static/tts）
_TTS_DIR = Path(__file__).resolve().parent.parent / "data" / "tts"


def _clean_tts_text(text: str) -> str:
    """Remove SSML and internal timing controls before text reaches the TTS engine."""
    cleaned = re.sub(r"<[^>]*>", "", text or "")
    cleaned = re.sub(
        r"(?<![A-Za-z])(?:wait(?:time)?|break(?:time)?|time)\s*[:=]\s*[\d.]+\s*(?:ms|s|sec|secs|seconds)?(?![A-Za-z])",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:break|wait)\s+time\s+is\s+(?:about\s+)?[\d.]+\s+"
        r"(?:ms|s|sec|secs|second|seconds)\b[.!?]?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()

# 情绪 → (Edge 音色, 语速)
# 调整思路：
# - 女性音色（XiaoxiaoNeural, XiaoyiNeural）更温柔亲近，适合亲密/温柔对白
# - 男性音色（YunxiNeural, YunjianNeural）更有力/温柔，适合叙述/故事
# - 语速微调：-10%~+10% 之间，避免过极端
# - 改进：降低语速极端化，让停顿承担更多表达
EMOTION_VOICE = {
    "happy": ("zh-CN-XiaoyiNeural", "+8%"),       # 开心：轻快女声，适度快速
    "sad": ("zh-CN-XiaoxiaoNeural", "-12%"),      # 难过：温柔女声，明显变慢（停顿帮助）
    "angry": ("zh-CN-YunjianNeural", "+5%"),      # 生气：有力男声，略快
    "gentle": ("zh-CN-XiaoxiaoNeural", "-8%"),    # 温柔：温柔女声，舒适慢速
    "neutral": ("zh-CN-XiaoxiaoNeural", "+2%"),   # 中性：温柔女声，接近常速
}


def _combine_rate(base: str, emotion_rate: str) -> str:
    """叠加基础语速与情绪语速：-5% + +30% = +25%。"""
    def val(s: str) -> int:
        return int(s.replace("+", "").replace("%", "").strip())
    total = val(base) + val(emotion_rate)
    return f"{'+' if total >= 0 else ''}{total}%"


class TTSClient:
    async def synthesize(
        self,
        text: str,
        emotion: str = "neutral",
        voice: str | None = None,
        rate: str | None = None,
    ) -> str:
        """生成语音，返回可访问 URL（/static/tts/xxx.mp3）。

        改进点：
        - 在句号/感叹号/问号后加停顿（提高自然度）
        - 语调微调（情感更明显）

        :param voice: 基础音色（角色性格音色），缺省用情绪默认
        :param rate:  基础语速（角色性格语速），情绪语速在它之上叠加
        """
        text = _clean_tts_text(text)
        if not text:
            raise ValueError("文本为空")

        # 【改进 1】添加停顿标记（暂时禁用 SSML，因为可能被念出来）
        # 在。！？后加停顿可以通过调整语速实现，而不是 SSML
        # edge_tts 有时会把 SSML 标签也念出来，所以先禁用此功能
        text_with_breaks = text

        import edge_tts

        _TTS_DIR.mkdir(parents=True, exist_ok=True)
        emotion_voice, emotion_rate = EMOTION_VOICE.get(emotion, EMOTION_VOICE["neutral"])
        final_voice = voice or emotion_voice
        # 暂时禁用 rate 参数，使用默认语速（防止参数混入）
        # final_rate = _combine_rate(rate, emotion_rate) if rate else emotion_rate

        filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
        file_path = _TTS_DIR / filename

        # 使用默认参数，不传 rate（防止参数被念出来）
        communicate = edge_tts.Communicate(text_with_breaks, final_voice)
        await communicate.save(str(file_path))

        return f"/static/tts/{filename}"

    @staticmethod
    def list_voices() -> list:
        """可用音色（前端选择用）。"""
        return [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓（女·默认）", "gender": "female"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓伊（女·轻快）", "gender": "female"},
            {"id": "zh-CN-YunxiNeural", "name": "云希（男·温柔）", "gender": "male"},
            {"id": "zh-CN-YunjianNeural", "name": "云健（男·有力）", "gender": "male"},
        ]
