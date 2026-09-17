"""
后台管理 - 数据导出 API 控制器（P2-09）
- 导出用户表（CSV/JSON）
- 导出消息表（按日期范围，CSV/JSON）
- 导出举报记录（按状态筛选，CSV/JSON）
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pydantic import BaseModel
import uuid
import csv
import json
from io import StringIO

from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from models.v1_0.message import Message
from models.report import Report

router = APIRouter()

# ===== Pydantic 模型 =====
class ExportRequest(BaseModel):
    format: str = "csv"  # csv 或 json
    limit: int = 10000

# ===== 权限检查 =====
async def check_admin(user: User = Depends(get_current_user)):
    """检查用户是否为管理员"""
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以访问"
        )
    return user

# ===== 导出用户表 =====
@router.get("/users", dependencies=[Depends(check_admin)])
async def export_users(
    format: str = Query("csv", pattern="^(csv|json)$"),
    limit: int = Query(10000, ge=1, le=100000),
    db: AsyncSession = Depends(get_db)
):
    """导出用户数据（CSV 或 JSON）"""
    try:
        # 查询用户
        stmt = select(User).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()

        if format == "json":
            # JSON 格式
            data = [
                {
                    "user_id": str(user.id),
                    "username": user.username,
                    "nickname": user.nickname,
                    "email": user.lunaris_id,  # 暂用 lunaris_id 作为邮箱
                    "gender": user.gender,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
                    "suspended_until": user.suspended_until.isoformat() if user.suspended_until else None,
                }
                for user in users
            ]
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            filename = f"users_{datetime.now().strftime('%Y%m%d')}.json"
            return StreamingResponse(
                iter([json_str]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
            )
        else:
            # CSV 格式
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "user_id", "username", "nickname", "email",
                "gender", "created_at", "last_seen_at", "suspended_until"
            ])

            for user in users:
                writer.writerow([
                    str(user.id),
                    user.username,
                    user.nickname or "",
                    user.lunaris_id or "",
                    user.gender,
                    user.created_at.isoformat() if user.created_at else "",
                    user.last_seen_at.isoformat() if user.last_seen_at else "",
                    user.suspended_until.isoformat() if user.suspended_until else "",
                ])

            csv_str = output.getvalue()
            filename = f"users_{datetime.now().strftime('%Y%m%d')}.csv"
            return StreamingResponse(
                iter([csv_str]),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出用户数据失败: {str(e)}"
        )

# ===== 导出消息表 =====
@router.get("/messages", dependencies=[Depends(check_admin)])
async def export_messages(
    format: str = Query("csv", pattern="^(csv|json)$"),
    from_date: str = Query(None),
    to_date: str = Query(None),
    limit: int = Query(10000, ge=1, le=100000),
    db: AsyncSession = Depends(get_db)
):
    """导出消息数据（按日期范围，CSV 或 JSON）"""
    try:
        stmt = select(Message)

        # 日期范围筛选
        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                stmt = stmt.where(Message.created_at >= from_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="from_date 格式错误，请用 ISO 8601 格式"
                )

        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                stmt = stmt.where(Message.created_at <= to_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="to_date 格式错误，请用 ISO 8601 格式"
                )

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        messages = result.scalars().all()

        if format == "json":
            # JSON 格式
            data = [
                {
                    "message_id": msg.id,
                    "sender_id": str(msg.user_id),
                    "sender_name": "",  # 需要 JOIN User 表获取
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "group_id": msg.conversation_id,
                    "conversation_id": msg.conversation_id,
                    "soul_id": msg.soul_id,
                }
                for msg in messages
            ]
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            filename = f"messages_{datetime.now().strftime('%Y%m%d')}.json"
            return StreamingResponse(
                iter([json_str]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
            )
        else:
            # CSV 格式
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "message_id", "sender_id", "sender_name", "content",
                "created_at", "group_id", "conversation_id", "soul_id"
            ])

            for msg in messages:
                writer.writerow([
                    msg.id,
                    str(msg.user_id),
                    "",
                    msg.content or "",
                    msg.created_at.isoformat() if msg.created_at else "",
                    msg.conversation_id or "",
                    msg.conversation_id or "",
                    msg.soul_id or "",
                ])

            csv_str = output.getvalue()
            filename = f"messages_{datetime.now().strftime('%Y%m%d')}.csv"
            return StreamingResponse(
                iter([csv_str]),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出消息数据失败: {str(e)}"
        )

# ===== 导出举报记录 =====
@router.get("/reports", dependencies=[Depends(check_admin)])
async def export_reports(
    format: str = Query("csv", pattern="^(csv|json)$"),
    status_filter: str = Query(None, pattern="^(pending|reviewing|approved|rejected|resolved)?$"),
    limit: int = Query(10000, ge=1, le=100000),
    db: AsyncSession = Depends(get_db)
):
    """导出举报记录（按状态筛选，CSV 或 JSON）"""
    try:
        stmt = select(Report)

        # 状态筛选
        if status_filter:
            stmt = stmt.where(Report.status == status_filter)

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        reports = result.scalars().all()

        if format == "json":
            # JSON 格式
            data = [
                {
                    "report_id": report.id,
                    "reporter_id": str(report.reporter_id),
                    "target_type": report.target_type,
                    "target_id": report.target_id,
                    "reason": report.reason,
                    "status": report.status,
                    "reviewed_by": str(report.reviewed_by) if report.reviewed_by else None,
                    "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
                    "created_at": report.created_at.isoformat() if report.created_at else None,
                }
                for report in reports
            ]
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            filename = f"reports_{datetime.now().strftime('%Y%m%d')}.json"
            return StreamingResponse(
                iter([json_str]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
            )
        else:
            # CSV 格式
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "report_id", "reporter_id", "target_type", "target_id",
                "reason", "status", "reviewed_by", "reviewed_at", "created_at"
            ])

            for report in reports:
                writer.writerow([
                    report.id,
                    str(report.reporter_id),
                    report.target_type,
                    report.target_id,
                    report.reason,
                    report.status,
                    str(report.reviewed_by) if report.reviewed_by else "",
                    report.reviewed_at.isoformat() if report.reviewed_at else "",
                    report.created_at.isoformat() if report.created_at else "",
                ])

            csv_str = output.getvalue()
            filename = f"reports_{datetime.now().strftime('%Y%m%d')}.csv"
            return StreamingResponse(
                iter([csv_str]),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出举报记录失败: {str(e)}"
        )
