"""
pytest 公共配置 —— 核心 fixtures 和数据库设置

【Fixtures】
- sys.path: 确保导入 backend 模块
- async_db: 异步数据库 session（每个测试独立事务）
- app: FastAPI 测试应用
- client: 测试客户端
- test_user: 测试用户（邮箱 test@example.com）
- test_soul: 测试角色（虚拟角色 Moon）
- test_moment: 测试动态
"""
import sys
from pathlib import Path
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# 导入路径设置
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config.database import Base
from main import create_app


# ============================================================
# 数据库 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def async_db():
    """
    异步数据库 session —— 每个测试在独立的事务中运行

    使用内存 SQLite（StaticPool）加速测试
    """
    # 使用 sqlite+aiosqlite 创建内存数据库
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,  # 设置为 True 可调试 SQL
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建 session
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield async_session

    # 清理
    await engine.dispose()


# ============================================================
# FastAPI App Fixtures
# ============================================================

@pytest.fixture
def app():
    """创建测试 FastAPI 应用"""
    return create_app()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


# ============================================================
# 用户 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def test_user(async_db):
    """
    创建测试用户

    邮箱: test@example.com
    用户名: testuser
    ID: 会自动生成 UUID
    """
    from models.user import User

    session = async_db()

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        nickname="Test User",
        password_hash="hashed_password",
        avatar_url="https://example.com/avatar.jpg",
        bio="Test bio",
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    yield user

    await session.close()


@pytest_asyncio.fixture
async def admin_user(async_db):
    """创建管理员用户"""
    from models.user import User

    session = async_db()

    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="admin",
        nickname="Admin User",
        password_hash="hashed_password",
        avatar_url="https://example.com/admin.jpg",
        bio="Admin",
        is_active=True,
        is_admin=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    yield admin

    await session.close()


@pytest_asyncio.fixture
async def second_user(async_db):
    """创建第二个测试用户（用于多用户测试）"""
    from models.user import User

    session = async_db()

    user = User(
        id=uuid.uuid4(),
        email="test2@example.com",
        username="testuser2",
        nickname="Test User 2",
        password_hash="hashed_password",
        avatar_url="https://example.com/avatar2.jpg",
        bio="Test bio 2",
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    yield user

    await session.close()


# ============================================================
# 角色 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def test_soul(async_db):
    """
    创建测试角色 —— Moon（月亮）

    虚拟伴侣角色，用于测试聊天功能
    """
    from models.soul import Soul

    session = async_db()

    soul = Soul(
        id=uuid.uuid4(),
        name="Moon",
        description="Mysterious Moon companion",
        category="companion",
        avatar_url="https://example.com/moon.jpg",
        personality="calm, wise, mysterious",
        greeting="Hello, I'm Moon. Nice to meet you.",
        is_active=True,
        visibility="public",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(soul)
    await session.commit()
    await session.refresh(soul)

    yield soul

    await session.close()


@pytest_asyncio.fixture
async def test_souls(async_db):
    """创建多个测试角色"""
    from models.soul import Soul

    session = async_db()

    souls_data = [
        ("Luna", "Night companion"),
        ("Star", "Dreamer"),
        ("Echo", "Reflective soul"),
    ]

    souls = []
    for name, description in souls_data:
        soul = Soul(
            id=uuid.uuid4(),
            name=name,
            description=description,
            category="companion",
            avatar_url=f"https://example.com/{name.lower()}.jpg",
            personality=f"{name.lower()} personality",
            greeting=f"Hello, I'm {name}.",
            is_active=True,
            visibility="public",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(soul)
        souls.append(soul)

    await session.commit()

    for soul in souls:
        await session.refresh(soul)

    yield souls

    await session.close()


# ============================================================
# 好友关系 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def test_friendship(async_db, test_user, second_user):
    """创建测试好友关系"""
    from models.friendship import Friendship

    session = async_db()

    friendship = Friendship(
        user_a_id=test_user.id,
        user_b_id=second_user.id,
        created_at=datetime.utcnow(),
    )

    session.add(friendship)
    await session.commit()
    await session.refresh(friendship)

    yield friendship

    await session.close()


# ============================================================
# 消息/会话 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def test_conversation(async_db, test_user, test_soul):
    """创建测试会话"""
    from models.conversation import Conversation

    session = async_db()

    conversation = Conversation(
        id=uuid.uuid4(),
        user_id=test_user.id,
        soul_id=test_soul.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    yield conversation

    await session.close()


@pytest_asyncio.fixture
async def test_message(async_db, test_conversation, test_user):
    """创建测试消息"""
    from models.message import Message

    session = async_db()

    message = Message(
        id=uuid.uuid4(),
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        content="Test message",
        role="user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(message)
    await session.commit()
    await session.refresh(message)

    yield message

    await session.close()


# ============================================================
# 朋友圈 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def test_moment(async_db, test_user, test_soul):
    """创建测试动态"""
    from models.moment import Moment

    session = async_db()

    moment = Moment(
        id=1,  # 通常 moment 用整数 ID
        soul_id=test_soul.id,
        content="Test moment content",
        images=[],
        topic_tags=["test", "moment"],
        is_published=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(moment)
    await session.commit()
    await session.refresh(moment)

    yield moment

    await session.close()


@pytest_asyncio.fixture
async def test_comment(async_db, test_moment, test_user):
    """创建测试评论"""
    from models.comment import Comment

    session = async_db()

    comment = Comment(
        id=1,
        moment_id=test_moment.id,
        user_id=test_user.id,
        content="Test comment",
        is_ai=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    yield comment

    await session.close()


# ============================================================
# 群聊 Fixtures
# ============================================================

@pytest_asyncio.fixture
async def test_group(async_db, test_user, test_soul):
    """创建测试群聊"""
    from models.group_chat import GroupChat

    session = async_db()

    group = GroupChat(
        id=1,
        soul_id=test_soul.id,
        name="Test Group",
        description="Test group for unit tests",
        owner_id=test_user.id,
        max_members=100,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(group)
    await session.commit()
    await session.refresh(group)

    yield group

    await session.close()


# ============================================================
# 工具函数
# ============================================================

@pytest.fixture
def create_test_token():
    """生成测试 JWT token 的工厂函数"""
    from jose import jwt
    from config.settings import get_settings

    settings = get_settings()

    def _create_token(user_id: uuid.UUID, expires_in_hours: int = 24) -> str:
        """创建 JWT token"""
        from datetime import timedelta

        expire = datetime.utcnow() + timedelta(hours=expires_in_hours)
        to_encode = {"sub": str(user_id), "exp": expire}
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm="HS256"
        )
        return encoded_jwt

    return _create_token

