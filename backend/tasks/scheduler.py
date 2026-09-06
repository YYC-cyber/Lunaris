"""
定时任务调度器（APScheduler）

【职责】
- 管理所有定时任务
- 启动时注册任务，关闭时优雅停止

【任务列表】
- 朋友圈定时发布：每天 08:00 和 20:00
- 热点缓存刷新：每小时
- 危机事件日报：每天 02:00
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from tasks.moments_task import run_moments_task
from tasks.hotspots_task import refresh_hotspots
from tasks.crisis_review_task import daily_report
from tasks.log_cleanup_task import cleanup_old_logs
from tasks.group_message_cleanup_task import cleanup_expired_messages
from tasks.crisis_cleanup_task import cleanup_crisis_events_task

# 全局调度器单例
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """获取或创建调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",  # 使用中国时区
            job_defaults={
                "coalesce": True,       # 多个积压任务合并执行一次
                "max_instances": 1,     # 同时最多运行一个实例
                "misfire_grace_time": 300,  # 错过执行后 5 分钟内补执行
            },
        )
    return _scheduler


def start_scheduler() -> None:
    """启动调度器（在应用启动时调用）"""
    scheduler = get_scheduler()

    # 注册朋友圈定时任务：每天 8:00 和 20:00
    scheduler.add_job(
        run_moments_task,
        trigger=CronTrigger(hour=8, minute=0),
        id="moments_08:00",
        name="朋友圈早8发动态",
        replace_existing=True,
    )
    scheduler.add_job(
        run_moments_task,
        trigger=CronTrigger(hour=20, minute=0),
        id="moments_20:00",
        name="朋友圈晚8发动态",
        replace_existing=True,
    )

    # 注册热点缓存任务：每小时
    scheduler.add_job(
        refresh_hotspots,
        trigger=IntervalTrigger(hours=1),
        id="hotspots_hourly",
        name="热点缓存刷新",
        replace_existing=True,
    )

    # 注册危机日报任务：每天 02:00
    scheduler.add_job(
        daily_report,
        trigger=CronTrigger(hour=2, minute=0),
        id="crisis_daily_report",
        name="危机事件日报",
        replace_existing=True,
    )

    # 注册日志清理任务：每天凌晨3点
    scheduler.add_job(
        cleanup_old_logs,
        trigger=CronTrigger(hour=3, minute=0),
        id="log_cleanup_daily",
        name="日志自动清理（3个月）",
        replace_existing=True,
    )

    # 注册群聊消息过期清理：每5分钟
    scheduler.add_job(
        cleanup_expired_messages,
        trigger=IntervalTrigger(minutes=5),
        id="group_message_cleanup_5min",
        name="群聊过期消息清理",
        replace_existing=True,
    )

    # 注册危机事件清理：每天凌晨 03:30（在日志清理之后）
    # PIPL 合规：保留 30 天后删除敏感的危机信息
    scheduler.add_job(
        cleanup_crisis_events_task,
        trigger=CronTrigger(hour=3, minute=30),
        id="crisis_cleanup_daily",
        name="危机事件清理（30天保留期）",
        replace_existing=True,
    )

    # 启动调度器（如果还没启动）
    if not scheduler.running:
        scheduler.start()
        print("⏰ 任务调度器已启动")
        print("   📱 朋友圈: 每天 08:00 和 20:00 自动发动态")
        print("   🔥 热点缓存: 每小时刷新")
        print("   🆘 危机日报: 每天 02:00")
        print("   🗑️  日志清理: 每天 03:00（清理3个月前的日志）")
        print("   💬 群聊消息清理: 每5分钟（清理过期消息）")
        print("   🔐 危机事件清理: 每天 03:30（PIPL：删除30天前的危机信息）")


def shutdown_scheduler() -> None:
    """关闭调度器（在应用关闭时调用）"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("⏰ 任务调度器已关闭")
        _scheduler = None


def get_job_status() -> list:
    """获取所有任务的状态（调试用）"""
    scheduler = get_scheduler()
    if not scheduler.running:
        return []
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        }
        for job in jobs
    ]