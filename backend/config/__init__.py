# config 包：应用配置
#
# 【内容】
# - settings.py：全局配置单例，统一从这里导入
#   from config.settings import get_settings
# - database.py：异步数据库引擎与会话
#   from config.database import engine, SessionLocal, Base, get_db
