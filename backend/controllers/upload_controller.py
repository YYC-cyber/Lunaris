"""文件上传控制器"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User

router = APIRouter()

# 上传文件保存目录
UPLOAD_DIR = "/tmp/lunaris_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/ogg", "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp4", "audio/aac",
}
MAX_AUDIO_SIZE = 20 * 1024 * 1024


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传用户图片

    返回: { "url": "/static/uploads/xxx.jpg" }
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名为空")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片类型。允许: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    try:
        # 读取文件内容
        content = await file.read()

        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"图片大小不能超过 {MAX_IMAGE_SIZE // 1024 // 1024}MB"
            )

        # 生成唯一文件名
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        # 保存文件
        with open(filepath, "wb") as f:
            f.write(content)

        # 返回可访问的 URL（假设静态文件服务在 /static/uploads/）
        url = f"/static/uploads/{filename}"

        return {
            "url": url,
            "filename": filename,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )


@router.post("/voice")
async def upload_voice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """保存用户语音文件并返回可播放 URL。"""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名为空")

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的音频格式")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空音频")
        if len(content) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="音频大小不能超过 20MB")

        ext = os.path.splitext(file.filename)[1].lower() or ".webm"
        filename = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
            f.write(content)

        return {
            "url": f"/static/uploads/{filename}",
            "filename": filename,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"语音上传失败: {str(e)}")
