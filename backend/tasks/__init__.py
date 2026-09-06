# tasks 包：定时任务（APScheduler）
#
# 【职责】
# - scheduler.py       调度器单例与启停
# - moments_task.py    每天 08:00 / 20:00 发朋友圈
# - hotspots_task.py   每小时拉取热点缓存
# - crisis_review_task.py 每天汇总危机事件（运营日报）
#
# 【说明】由 main.py lifespan 启动；任务内部用 notify_service 推送
