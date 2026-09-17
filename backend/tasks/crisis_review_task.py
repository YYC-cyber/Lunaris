"""
危机事件日报任务 —— 每天汇总 high/critical 危机事件，输出结构化日志报告。

【职责】
- daily_report()
  每天 02:00 执行：
  1. 统计近 24h 危机事件（按 risk_level 分组，计数 + 去重用户数）
  2. 输出结构化日志报告（用户数 / 事件数 / high+critical 明细摘要）
  3. 预留：风险指标超阈值 → 通知运营（SAFE-06 人为介入预留）

【说明】
- 本任务不干预在线服务，仅做运营侧汇总。
- 用 to_regclass 探测表是否存在，未建表（未跑迁移）时静默跳过，避免任务报错。
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from config.database import AsyncSessionLocal

# 触发人工介入预留的阈值（SAFE-06，后续可接通知）
_ESCALATE_THRESHOLD = 10


async def daily_report() -> dict:
    """统计近 24h 危机事件并输出报告。返回汇总 dict 供测试/日志二次使用。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC，与列一致
    since = now - timedelta(hours=24)

    async with AsyncSessionLocal() as db:
        exists = (
            await db.execute(text("SELECT to_regclass('crisis_events')"))
        ).scalar()
        if not exists:
            print("⏭️ 危机日报：crisis_events 表未建，跳过")
            return {"skipped": True}

        from models.v1_0.crisis_event import CrisisEvent

        # 按风险级别分组计数 + 去重用户数
        rows = (
            await db.execute(
                select(
                    CrisisEvent.risk_level,
                    func.count(CrisisEvent.id),
                    func.count(func.distinct(CrisisEvent.user_id)),
                )
                .where(CrisisEvent.handled_at >= since)
                .group_by(CrisisEvent.risk_level)
            )
        ).all()

        # high/critical 明细（最多 20 条摘要）
        from sqlalchemy import desc
        details = (
            await db.execute(
                select(CrisisEvent)
                .where(
                    CrisisEvent.handled_at >= since,
                    CrisisEvent.risk_level.in_(["high", "critical"]),
                )
                .order_by(desc(CrisisEvent.handled_at))
                .limit(20)
            )
        ).scalars().all()

    summary = {r: {"count": c, "users": u} for r, c, u in rows}
    total = sum(v["count"] for v in summary.values())
    high_critical = sum(v["count"] for r, v in summary.items() if r in ("high", "critical"))

    print("=" * 50)
    print(f"🆘 危机事件日报（{since.isoformat()} ~ {now.isoformat()}）")
    print(f"   总事件: {total}")
    for r in ("warning", "high", "critical"):
        if r in summary:
            s = summary[r]
            print(f"   - {r}: {s['count']} 起 / 涉及 {s['users']} 位用户")
    print(f"   高危(hight+critical): {high_critical} 起")
    if details:
        print("   ── 高危明细 ──")
        for d in details:
            print(f"   [{d.risk_level}] user={d.user_id} soul={d.soul_id} "
                  f"「{d.trigger_content[:30]}…」 {d.handled_at}")
    if high_critical >= _ESCALATE_THRESHOLD:
        print(f"   ⚠️ 高危事件达 {high_critical} 起，超阈值 {_ESCALATE_THRESHOLD}，建议人工介入（SAFE-06）")
    print("=" * 50)

    return {"total": total, "high_critical": high_critical, "by_level": summary}
