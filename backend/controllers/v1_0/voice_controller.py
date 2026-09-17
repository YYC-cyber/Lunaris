# backend/controllers/voice_controller.py
"""语音路由（CHAT-03）—— 用户语音转文字（本地 whisper.cpp，免 key）。

【流程】
前端录音 → POST /api/voice/transcribe（上传音频）→ 返回文字 → 前端把文字当普通消息发聊天
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from clients.tts_client import TTSClient
from clients.whisper_client import WhisperClient
from config.database import get_db
from config.settings import get_settings
from middleware.auth_middleware import get_current_user
from models.user import User

router = APIRouter()
settings = get_settings()


class TTSIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    emotion: str = Field("neutral", pattern="^(happy|sad|angry|gentle|neutral)$")
    voice: str | None = None
    soul_id: int | None = None   # 指定角色 → 用该角色性格音色/语速

# 上传上限（20MB）
MAX_AUDIO_SIZE = 20 * 1024 * 1024


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """上传语音 → 本地 whisper.cpp 转文字（免 key）。"""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="音频过大（>20MB）")

    client = WhisperClient()
    try:
        text = await client.transcribe(
            audio_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"转写失败: {e}")

    return {"text": text}


@router.get("/status")
async def voice_status(user: User = Depends(get_current_user)):
    """本地 whisper 就绪状态（前端据此提示「语音可用」或「未安装」）。"""
    binary_ok, model_ok = WhisperClient().check_ready()
    return {
        "use_local": settings.WHISPER_USE_LOCAL,
        "local_ready": binary_ok and model_ok,
        "binary_ok": binary_ok,
        "model_ok": model_ok,
        "hint": "运行 scripts/setup_whisper.py 安装本地 whisper" if not (binary_ok and model_ok) else None,
    }


@router.post("/synthesize")
async def synthesize(
    data: TTSIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """文字转语音（Edge TTS 免 key）。

    soul_id 指定时用该角色性格音色/语速，情绪再叠加。
    """
    voice, rate = data.voice, None
    if data.soul_id:
        from dao.v1_0.soul_dao import SoulDAO
        soul = await SoulDAO.get(db, data.soul_id)
        if not soul:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
        voice = soul.tts_voice or voice
        rate = soul.tts_rate

    client = TTSClient()
    try:
        url = await client.synthesize(data.text, data.emotion, voice, rate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"TTS 合成失败: {e}")
    return {"url": url, "emotion": data.emotion, "voice": voice, "rate": rate}


@router.get("/voices")
async def list_voices(user: User = Depends(get_current_user)):
    """可用 TTS 音色列表。"""
    return {"data": TTSClient.list_voices()}
