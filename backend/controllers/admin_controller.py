"""
后台管理 API 控制器 - 用户、统计、监控、异常管理
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, desc, String
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import psutil
import uuid

from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from models.system_log import SystemLog
from services.auth_service import AuthService
from pydantic import BaseModel

router = APIRouter()

# ===== Pydantic 模型 =====
class UserUpdate(BaseModel):
    username: str
    gender: str
    nickname: str | None = None

# ===== 权限检查 =====
async def check_admin(user: User = Depends(get_current_user)):
    """检查用户是否为管理员"""
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以访问"
        )
    return user

# ===== 用户管理 =====
@router.get("/users", dependencies=[Depends(check_admin)])
async def get_users(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 20):
    """获取用户列表"""
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "data": [
            {
                "id": str(u.id),
                "username": u.username,
                "gender": u.gender,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": len(users)
    }

@router.get("/users/stats", dependencies=[Depends(check_admin)])
async def get_users_stats(db: AsyncSession = Depends(get_db)):
    """获取用户统计"""
    # 总用户数
    total_query = select(func.count(User.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # 今日新增
    today = datetime.now().date()
    today_query = select(func.count(User.id)).where(
        func.cast(User.created_at, String).like(f"{today}%")
    )
    today_result = await db.execute(today_query)
    new_today = today_result.scalar() or 0

    # 活跃用户（最近7天有消息的用户）
    from models.message import Message
    seven_days_ago = datetime.now() - timedelta(days=7)
    active_query = select(func.count(func.distinct(Message.user_id))).where(
        Message.created_at >= seven_days_ago
    )
    active_result = await db.execute(active_query)
    active_users = active_result.scalar() or 0

    # 用户增长趋势（过去7天）
    user_growth = []
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).date()
        count_query = select(func.count(User.id)).where(
            func.cast(User.created_at, String).like(f"{day}%")
        )
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0
        user_growth.append({"date": day.isoformat(), "count": count})

    user_growth.reverse()

    return {
        "total_users": total,
        "active_users": active_users,
        "new_users_today": new_today,
        "user_growth": user_growth
    }

@router.post("/users", dependencies=[Depends(check_admin)])
async def create_user(db: AsyncSession = Depends(get_db), username: str = None, password: str = None, gender: str = 'male'):
    """创建新用户"""
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码必填")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar():
        raise HTTPException(status_code=400, detail="用户名已存在")

    password_hash = AuthService.hash_password(password)

    new_user = User(
        id=uuid.uuid4(),
        username=username,
        password_hash=password_hash,
        gender=gender,
        is_active=True
    )
    db.add(new_user)
    await db.commit()

    return {"id": str(new_user.id), "username": new_user.username, "message": "用户创建成功"}

@router.put("/users/{user_id}", dependencies=[Depends(check_admin)])
async def update_user(user_id: str, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """更新用户信息"""
    user = await db.execute(select(User).where(User.id == user_id))
    user_obj = user.scalar()

    if not user_obj:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_obj.username = data.username
    user_obj.gender = data.gender
    if data.nickname:
        user_obj.nickname = data.nickname

    await db.commit()
    return {"message": "用户更新成功", "id": str(user_obj.id)}

@router.delete("/users/{user_id}", dependencies=[Depends(check_admin)])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """删除用户（标记停用）"""
    user = await db.execute(select(User).where(User.id == user_id))
    user_obj = user.scalar()

    if not user_obj:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_obj.is_active = False
    await db.commit()
    return {"message": "用户已停用"}

# ===== 数据统计 =====
@router.get("/analytics/dashboard", dependencies=[Depends(check_admin)])
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """获取仪表盘统计"""
    from models.message import Message
    from models.soul import Soul
    from models.sticker import Sticker
    from models.sticker_favorite import StickerFavorite

    # 总用户数（已实现）
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    # 活跃用户（最近7天有消息）
    seven_days_ago = datetime.now() - timedelta(days=7)
    active_query = select(func.count(func.distinct(Message.user_id))).where(
        Message.created_at >= seven_days_ago
    )
    active_result = await db.execute(active_query)
    active_users = active_result.scalar() or 0

    # 今日新增用户
    today = datetime.now().date()
    today_query = select(func.count(User.id)).where(
        func.cast(User.created_at, String).like(f"{today}%")
    )
    today_result = await db.execute(today_query)
    new_users_today = today_result.scalar() or 0

    # 消息总数
    msg_count = await db.execute(select(func.count(Message.id)))
    total_messages = msg_count.scalar() or 0

    # 表情收藏数
    sticker_fav_count = await db.execute(select(func.count(StickerFavorite.id)))
    total_stickers = sticker_fav_count.scalar() or 0

    # 语音消息数
    voice_count = await db.execute(
        select(func.count(Message.id)).where(Message.voice_url.isnot(None))
    )
    total_voices = voice_count.scalar() or 0

    # 消息趋势（过去7天）
    message_trend = []
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).date()
        day_count_query = select(func.count(Message.id)).where(
            func.cast(Message.created_at, String).like(f"{day}%")
        )
        day_count_result = await db.execute(day_count_query)
        count = day_count_result.scalar() or 0
        message_trend.append({"date": day.isoformat(), "count": count})
    message_trend.reverse()

    # 表情分布（按情绪）
    sticker_dist_query = select(Sticker.emotion, func.count(Message.id)).where(
        Message.msg_type == "sticker", Message.sticker_id.isnot(None)
    ).join(Sticker, Message.sticker_id == Sticker.id).group_by(Sticker.emotion)
    sticker_dist_result = await db.execute(sticker_dist_query)
    sticker_dist_rows = sticker_dist_result.all() or []
    sticker_distribution = [{"emotion": row[0], "count": row[1]} for row in sticker_dist_rows]

    # 角色排行（按消息数）
    top_souls_query = select(Soul.display_name, func.count(Message.id)).where(
        Message.soul_id.isnot(None)
    ).join(Soul, Message.soul_id == Soul.id).group_by(Soul.id, Soul.display_name).order_by(desc(func.count(Message.id))).limit(5)
    top_souls_result = await db.execute(top_souls_query)
    top_souls_rows = top_souls_result.all() or []
    top_souls = [{"name": row[0], "count": row[1]} for row in top_souls_rows]

    # 用户活跃度（过去7天，按天）
    user_activity = []
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).date()
        day_active_query = select(func.count(func.distinct(Message.user_id))).where(
            func.cast(Message.created_at, String).like(f"{day}%")
        )
        day_active_result = await db.execute(day_active_query)
        active_count = day_active_result.scalar() or 0
        user_activity.append({"date": day.isoformat(), "active_count": active_count})
    user_activity.reverse()

    # 聊天频率（按小时）
    chat_frequency = []
    for hour in range(24):
        hour_query = select(func.count(Message.id)).where(
            func.extract('hour', Message.created_at) == hour
        )
        hour_result = await db.execute(hour_query)
        count = hour_result.scalar() or 0
        chat_frequency.append({"hour": hour, "count": count})

    # 消息情绪分布（按emotion字段）
    sentiment_query = select(Message.emotion, func.count(Message.id)).group_by(Message.emotion)
    sentiment_result = await db.execute(sentiment_query)
    sentiment_rows = sentiment_result.all() or []
    total_sentiment_count = sum(row[1] for row in sentiment_rows)
    message_sentiment = []
    for emotion, count in sentiment_rows:
        if emotion:
            message_sentiment.append({
                "sentiment": emotion,
                "count": count,
                "percent": round(100 * count / total_sentiment_count, 1) if total_sentiment_count > 0 else 0
            })

    return {
        "total_users": total_users,
        "active_users": active_users,
        "new_users_today": new_users_today,
        "total_messages": total_messages,
        "total_stickers": total_stickers,
        "total_voices": total_voices,
        "message_trend": message_trend,
        "sticker_distribution": sticker_distribution,
        "top_souls": top_souls,
        "user_activity": user_activity,
        "chat_frequency": chat_frequency,
        "message_sentiment": message_sentiment
    }

@router.get("/analytics/messages", dependencies=[Depends(check_admin)])
async def get_message_stats(db: AsyncSession = Depends(get_db)):
    """获取消息统计（新增表情包分布）"""
    from models.message import Message
    from models.sticker import Sticker

    # 总消息数
    total_query = select(func.count(Message.id))
    total_result = await db.execute(total_query)
    total_messages = total_result.scalar() or 0

    # 日均消息数（过去30天）
    thirty_days_ago = datetime.now() - timedelta(days=30)
    daily_query = select(func.count(Message.id)).where(Message.created_at >= thirty_days_ago)
    daily_result = await db.execute(daily_query)
    daily_count = daily_result.scalar() or 0
    daily_average = round(daily_count / 30) if daily_count > 0 else 0

    # 按小时分布
    hourly_distribution = []
    for hour in range(24):
        hour_query = select(func.count(Message.id)).where(
            func.extract('hour', Message.created_at) == hour
        )
        hour_result = await db.execute(hour_query)
        count = hour_result.scalar() or 0
        hourly_distribution.append({"hour": hour, "count": count})

    # 按消息类型分布
    type_query = select(Message.msg_type, func.count(Message.id)).group_by(Message.msg_type)
    type_result = await db.execute(type_query)
    type_rows = type_result.all() or []
    total_by_type = sum(row[1] for row in type_rows)
    message_types = []
    for msg_type, count in type_rows:
        message_types.append({
            "type": msg_type or "unknown",
            "count": count,
            "percent": round(100 * count / total_by_type, 1) if total_by_type > 0 else 0
        })

    # 🆕 表情包分布（按情绪分类）
    sticker_query = (
        select(Sticker.emotion, func.count(Message.id))
        .join(Sticker, Message.sticker_id == Sticker.id)
        .where(Message.msg_type == "sticker", Message.sticker_id.isnot(None))
        .group_by(Sticker.emotion)
    )
    sticker_result = await db.execute(sticker_query)
    sticker_rows = sticker_result.all() or []
    stickers = [
        {"emotion": row[0] or "未分类", "count": int(row[1])}
        for row in sticker_rows
    ]

    return {
        "total_messages": total_messages,
        "daily_average": daily_average,
        "hourly_distribution": hourly_distribution,
        "message_types": message_types,
        "stickers": stickers  # NEW
    }

# ===== 系统监控 =====
@router.get("/monitoring/system", dependencies=[Depends(check_admin)])
async def get_system_status():
    """获取系统状态"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        "status": "healthy",
        "db_status": "connected",
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "memory_used": f"{memory.used / (1024**3):.2f} GB",
        "memory_total": f"{memory.total / (1024**3):.2f} GB",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/monitoring/errors", dependencies=[Depends(check_admin)])
async def get_error_logs(db: AsyncSession = Depends(get_db)):
    """获取错误日志（从系统日志表查询status=fail的记录）"""
    # 查询所有失败的操作
    fail_logs_query = select(SystemLog).where(SystemLog.status == 'fail').order_by(desc(SystemLog.created_at)).limit(100)
    fail_logs_result = await db.execute(fail_logs_query)
    fail_logs = fail_logs_result.scalars().all()

    # 分类统计
    critical_count = sum(1 for log in fail_logs if 'error' in log.action.lower() or 'exception' in log.action.lower())
    warning_count = sum(1 for log in fail_logs if 'warning' in log.action.lower() or 'failed' in log.action.lower())
    info_count = len(fail_logs) - critical_count - warning_count

    # 构建错误列表（前10条）
    recent_errors = []
    error_groups = {}
    for log in fail_logs[:50]:
        key = f"{log.action}:{log.details[:50]}" if log.details else log.action
        if key not in error_groups:
            error_groups[key] = {'log': log, 'count': 0}
        error_groups[key]['count'] += 1

    for i, (key, item) in enumerate(list(error_groups.items())[:10]):
        log = item['log']
        recent_errors.append({
            "id": log.id,
            "type": log.action,
            "message": log.details or '操作失败',
            "severity": "critical" if item['count'] > 3 else "warning" if item['count'] > 1 else "info",
            "timestamp": log.created_at.isoformat(),
            "count": item['count']
        })

    return {
        "total_errors": len(fail_logs),
        "critical": critical_count,
        "warning": warning_count,
        "info": info_count,
        "recent_errors": recent_errors
    }

# ===== 异常管理 =====
@router.get("/exceptions/list", dependencies=[Depends(check_admin)])
async def get_exceptions(db: AsyncSession = Depends(get_db)):
    """获取异常列表（从系统日志查询）"""
    fail_query = select(SystemLog).where(SystemLog.status == 'fail').order_by(desc(SystemLog.created_at)).limit(100)
    fail_result = await db.execute(fail_query)
    fail_logs = fail_result.scalars().all()

    # 按 action 分组计数
    exception_groups = {}
    for log in fail_logs:
        key = log.action
        if key not in exception_groups:
            exception_groups[key] = {'message': log.details or '操作失败', 'count': 0, 'timestamp': log.created_at}
        exception_groups[key]['count'] += 1

    exceptions = []
    for i, (exc_type, data) in enumerate(list(exception_groups.items())[:10]):
        exceptions.append({
            "id": i + 1,
            "type": exc_type,
            "message": data['message'],
            "count": data['count'],
            "severity": "critical" if data['count'] > 5 else "warning" if data['count'] > 2 else "info",
            "timestamp": data['timestamp'].isoformat()
        })

    return {
        "total_exceptions": len(fail_logs),
        "exceptions": exceptions
    }

@router.get("/exceptions/trend", dependencies=[Depends(check_admin)])
async def get_exception_trend(db: AsyncSession = Depends(get_db)):
    """获取异常趋势（过去7天）"""
    # 按天统计异常
    trend = []
    exception_types = {}

    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).date()
        day_query = select(func.count(SystemLog.id), SystemLog.action).where(
            func.cast(SystemLog.created_at, String).like(f"{day}%"),
            SystemLog.status == 'fail'
        ).group_by(SystemLog.action)
        day_result = await db.execute(day_query)
        day_rows = day_result.all() or []

        day_total = sum(row[0] for row in day_rows)
        trend.append({"date": day.isoformat(), "count": day_total})

        # 统计异常类型
        for count, action in day_rows:
            if action not in exception_types:
                exception_types[action] = 0
            exception_types[action] += count

    trend.reverse()

    # 按发生次数排序，取前5种
    total_exceptions = sum(exception_types.values())
    types_dist = []
    for exc_type, count in sorted(exception_types.items(), key=lambda x: x[1], reverse=True)[:5]:
        types_dist.append({
            "type": exc_type,
            "count": count,
            "percent": round(100 * count / total_exceptions, 1) if total_exceptions > 0 else 0
        })

    return {
        "trend": trend,
        "types_distribution": types_dist
    }

# ===== 系统日志 =====
@router.get("/logs", dependencies=[Depends(check_admin)])
async def get_system_logs(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 50):
    """获取系统日志"""
    query = select(SystemLog).order_by(desc(SystemLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    total_query = select(func.count(SystemLog.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    return {
        "data": [log.to_dict() for log in logs],
        "total": total
    }

@router.get("/logs/actions", dependencies=[Depends(check_admin)])
async def get_log_actions(db: AsyncSession = Depends(get_db)):
    """获取日志统计"""
    actions = await db.execute(select(SystemLog.action, func.count(SystemLog.id)).group_by(SystemLog.action))
    result = actions.all()

    return {
        "actions": [
            {"action": r[0], "count": r[1]}
            for r in result
        ]
    }

@router.get("/analytics/advanced", dependencies=[Depends(check_admin)])
async def get_advanced_analytics(db: AsyncSession = Depends(get_db)):
    """获取高级分析数据（使用真实数据库查询）"""
    from models.message import Message
    from models.soul import Soul
    from sqlalchemy import extract

    thirty_days_ago = datetime.now() - timedelta(days=30)

    # 1️⃣ 热力图：按星期几和小时统计消息数（真实数据）
    heatmap_query = select(
        extract('dow', Message.created_at).label('day'),
        extract('hour', Message.created_at).label('hour'),
        func.count(Message.id).label('value')
    ).group_by('day', 'hour')
    heatmap_result = await db.execute(heatmap_query)
    heatmap_rows = heatmap_result.all()
    heatmap_data = [
        {"day": int(row[0]), "hour": int(row[1]), "value": int(row[2])}
        for row in heatmap_rows
    ]

    # 2️⃣ 散点图：最活跃 50 用户（真实数据）
    scatter_query = (
        select(
            Message.user_id,
            func.count(func.distinct(func.date(Message.created_at))).label('active_days'),
            func.count(Message.id).label('message_count')
        )
        .where(Message.created_at >= thirty_days_ago, Message.user_id.isnot(None))
        .group_by(Message.user_id)
        .order_by(desc(func.count(Message.id)))
        .limit(50)
    )
    scatter_result = await db.execute(scatter_query)
    scatter_rows = scatter_result.all()
    scatter_data = [
        {
            "x": int(row[1]),  # active_days
            "y": int(row[2]),  # message_count
            "size": min(100, int(row[2] / 2)),
            "name": f"用户{str(row[0])[:8]}"
        }
        for row in scatter_rows
    ]

    # 3️⃣ 树形图：按 Soul→Emotion 分布（真实数据）
    tree_query = (
        select(Soul.display_name, Message.emotion, func.count(Message.id))
        .join(Soul, Message.soul_id == Soul.id)
        .where(Message.emotion.isnot(None))
        .group_by(Soul.display_name, Message.emotion)
    )
    tree_result = await db.execute(tree_query)
    tree_rows = tree_result.all()

    # 组织树结构
    tree_dict = {}
    for soul_name, emotion, count in tree_rows:
        if soul_name not in tree_dict:
            tree_dict[soul_name] = {"name": soul_name, "children": []}
        tree_dict[soul_name]["children"].append(
            {"name": emotion or "未分类", "value": int(count)}
        )
    tree_data = {
        "name": "Lunaris Users",
        "children": list(tree_dict.values())
    }

    # 4️⃣ 桑基图：Soul→消息级别分布（按消息数在应用层划分轻度/中度/重度）
    soul_count_query = (
        select(Soul.display_name, func.count(Message.id).label('count'))
        .join(Soul, Message.soul_id == Soul.id)
        .where(Message.user_id.isnot(None))  # 仅真实用户消息
        .group_by(Soul.display_name)
    )
    soul_count_result = await db.execute(soul_count_query)
    soul_count_rows = soul_count_result.all()

    def classify_tier(n: int) -> str:
        if n < 10:
            return '轻度'
        if n < 50:
            return '中度'
        return '重度'

    # 构建桑基图数据
    souls = sorted({row[0] for row in soul_count_rows})
    tiers = ['轻度', '中度', '重度']
    sankey_nodes = [{"name": s} for s in souls] + [{"name": t} for t in tiers]
    sankey_links = []
    for soul_name, count in soul_count_rows:
        tier = classify_tier(int(count))
        sankey_links.append({
            "source": souls.index(soul_name),
            "target": len(souls) + tiers.index(tier),
            "value": int(count)
        })

    return {
        "heatmap_data": heatmap_data,
        "scatter_data": scatter_data,
        "tree_data": tree_data,
        "sankey_data": {"nodes": sankey_nodes, "links": sankey_links}
        # 注：funnel_data 已删除（无事件追踪数据可用）
    }

# ===== 权限管理 =====
@router.get("/roles", dependencies=[Depends(check_admin)])
async def get_all_roles():
    """获取所有角色"""
    return {
        "roles": [
            {"id": "1", "name": "admin", "description": "管理员，拥有所有权限"},
            {"id": "2", "name": "manager", "description": "经理，可管理用户和查看报表"},
            {"id": "3", "name": "user", "description": "普通用户，仅可查看自己的数据"}
        ]
    }

@router.put("/users/{user_id}/role", dependencies=[Depends(check_admin)])
async def update_user_role(user_id: str, role: str, db: AsyncSession = Depends(get_db)):
    """更新用户角色"""
    if role not in ["admin", "manager", "user"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    user = await db.execute(select(User).where(User.id == user_id))
    user_obj = user.scalar()

    if not user_obj:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_obj.role = role
    await db.commit()
    return {"message": "角色更新成功", "user_id": str(user_obj.id), "role": user_obj.role}

@router.get("/permissions", dependencies=[Depends(check_admin)])
async def get_permissions():
    """获取权限列表"""
    return {
        "permissions": [
            {"id": "1", "name": "users.view", "description": "查看用户列表"},
            {"id": "2", "name": "users.create", "description": "创建用户"},
            {"id": "3", "name": "users.edit", "description": "编辑用户"},
            {"id": "4", "name": "users.delete", "description": "删除用户"},
            {"id": "5", "name": "reports.view", "description": "查看报表"},
            {"id": "6", "name": "settings.edit", "description": "编辑系统设置"},
            {"id": "7", "name": "logs.view", "description": "查看操作日志"}
        ],
        "role_permissions": {
            "admin": ["users.view", "users.create", "users.edit", "users.delete", "reports.view", "settings.edit", "logs.view"],
            "manager": ["users.view", "users.create", "users.edit", "reports.view", "logs.view"],
            "user": ["users.view", "reports.view"]
        }
    }
