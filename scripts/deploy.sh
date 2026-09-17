#!/usr/bin/env bash
# =============================================================
# Lunaris 一键部署脚本 —— 框架占位，按注释实现。
# 目标：Ubuntu 22.04 LTS 服务器（中国大陆地域）
# 详细步骤见 .docs/DEPLOYMENT.md
# =============================================================
set -euo pipefail

# 1. 系统初始化
#    apt update && apt install -y python3.11 python3.11-venv postgresql-15 postgresql-15-pgvector nginx git

# 2. 创建数据库（pgvector 扩展）
#    sudo -u postgres createdb lunaris_db
#    sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;" lunaris_db
#    sudo -u postgres psql -c "CREATE USER lunaris WITH PASSWORD '...';"
#    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lunaris_db TO lunaris;"

# 3. 拉取代码
#    git clone <repo> /opt/lunaris && cd /opt/lunaris

# 4. 安装依赖（uv）
#    curl -LsSf https://astral.sh/uv/install.sh | sh
#    uv sync

# 5. 配置 .env（从 backend/.env 模板复制并填写密钥）

# 6. 数据库迁移 + 种子数据
#    uv run alembic upgrade head
#    uv run python scripts/init_db.py

# 7. 启动服务（systemd 建议）
#    uv run gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app \
#        --bind 127.0.0.1:8000

# 8. Nginx 反向代理（443 HTTPS + WS upgrade）
#    - location / { proxy_pass http://127.0.0.1:8000; }
#    - location /ws {
#        proxy_pass http://127.0.0.1:8000;
#        proxy_http_version 1.1;
#        proxy_set_header Upgrade $http_upgrade;
#        proxy_set_header Connection "upgrade";
#        proxy_read_timeout 300s;
#      }
