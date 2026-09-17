# ============================================================
# Lunaris 后端 Dockerfile
# 基于 uv 管理依赖，Python 3.11（与 pyproject.toml 一致）
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装 uv（Python 包管理器）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制依赖清单
COPY pyproject.toml ./

# 创建虚拟环境并安装依赖（只装运行依赖，跳过 dev）
RUN uv venv /opt/venv --python 3.11 \
    && uv pip install --python /opt/venv/bin/python --no-cache-dir \
        fastapi uvicorn[standard] python-multipart \
        sqlalchemy[asyncio] asyncpg alembic \
        pgvector gunicorn \
        pyjwt bcrypt passlib pydantic-settings httpx \
        textfilter apscheduler loguru \
        psycopg2-binary \
        python-jose websockets edge-tts \
        psutil cryptography

# ============================================================
# 运行阶段
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .
WORKDIR /app/backend
ENV PYTHONPATH="/app/backend"

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令（生产环境）
CMD ["sh", "-c", "alembic -c alembic/alembic.ini upgrade head && gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app"]
