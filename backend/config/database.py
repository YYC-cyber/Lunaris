"""
数据库连接（异步 SQLAlchemy + asyncpg）—— 框架占位，按注释实现。

【内容】
1. create_async_engine(settings.DATABASE_URL)
   - echo=False，pool_pre_ping=True（断线自动重连）
2. async_sessionmaker(expire_on_commit=False)  → 导出 SessionLocal
3. Base = DeclarativeBase  → 所有 models 继承它
   from config.database import Base
4. get_db() FastAPI 依赖
   async def get_db() -> AsyncIterator[AsyncSession]:
       async with SessionLocal() as session:
           yield session
   # 供 controllers 通过 Depends(get_db) 注入会话
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .settings import get_settings

# 加载配置
settings = get_settings()

# 创建一步数据库引擎
# echo =True 会在控制台打印sql语句,方便调试()生产环境可关闭
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True # 连接前自动检查连接是否有效
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False # 提交后不使对象过期（方便后续操作）
)

# 声明基类(后续所有ORM 模型都继承它)
Base = declarative_base()

# 依赖注入函数: 用于FastAPI 路由中获取数据库会话
async def get_db()->AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # 会话会在上下文结束时自动关闭
            pass




