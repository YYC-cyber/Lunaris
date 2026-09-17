# 🐳 Lunaris Docker 部署指南

## 前置要求

- Docker >= 24.0
- Docker Compose >= 2.20
- 至少 4GB 可用内存

## 快速开始

### 1️⃣ 准备环境配置

```bash
# 复制 Docker 环境变量模板
cp .env.docker .env

# 编辑 .env 并填入真实的密钥和配置
# 必须修改以下值：
# - POSTGRES_PASSWORD （数据库密码）
# - REDIS_PASSWORD （Redis 缓存密码）
# - JWT_SECRET （认证密钥）
# - ENCRYPTION_KEY （加密密钥）
# - DEEPSEEK_API_KEY （如需 AI 功能）

nano .env
```

### 2️⃣ 生成新的密钥（如果 .env 中还没有）

```bash
# 生成 JWT_SECRET（64 字符十六进制）
python3 -c "import secrets; print(secrets.token_hex(32))"

# 生成 ENCRYPTION_KEY（64 字符十六进制）
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3️⃣ 启动容器

```bash
# 构建镜像并启动所有服务（后台运行）
docker compose up -d --build

# 查看启动日志
docker compose logs -f

# 查看具体服务日志
docker compose logs -f backend
docker compose logs -f db
docker compose logs -f frontend
```

### 4️⃣ 初始化数据库

```bash
# 运行数据库迁移（自动执行，但可手动触发）
docker compose exec backend alembic -c alembic/alembic.ini upgrade head

# 初始化演示数据（可选）
docker compose exec backend python scripts/init_souls.py
docker compose exec backend python scripts/init_stickers.py
```

### 5️⃣ 验证服务状态

```bash
# 查看所有容器状态
docker compose ps

# 检查后端健康状态
curl http://localhost:8001/health

# 访问应用
# 前端: http://localhost:3000
# API: http://localhost:8001
# 数据库（本地连接）: localhost:5432
# Redis（本地连接）: localhost:6379
```

## 📊 服务详情

| 服务 | 容器名 | 端口 | 健康检查 |
|------|--------|------|---------|
| PostgreSQL | lunaris-db | 5432 | pg_isready |
| Redis | lunaris-cache | 6379 | redis-cli ping |
| 后端 API | lunaris-backend | 8001 (→ 8000) | GET /health |
| 前端 | lunaris-frontend | 3000 (→ 80) | GET / |

## 🛠️ 常用命令

### 停止服务
```bash
docker compose down
```

### 停止并删除所有数据（谨慎！）
```bash
docker compose down -v
```

### 重启特定服务
```bash
docker compose restart backend
docker compose restart db
```

### 查看实时日志
```bash
docker compose logs -f --tail 100
```

### 进入容器调试
```bash
# 进入后端容器
docker compose exec backend bash

# 进入数据库容器
docker compose exec db psql -U lunaris -d lunaris_db

# 进入 Redis 容器
docker compose exec cache redis-cli
```

## 📁 持久化卷

```bash
# 查看所有卷
docker volume ls | grep lunaris

# 查看卷详情
docker volume inspect lunaris_pgdata
docker volume inspect lunaris_redisdata
```

## 🔒 安全建议

1. **生产环境必备**：
   - 更改所有默认密码
   - 使用强随机密钥（不要硬编码）
   - 启用 HTTPS（使用 Nginx/Traefik 反向代理）
   - 限制数据库外部访问（关闭 5432、6379 的公网暴露）

2. **备份策略**：
   ```bash
   # 备份 PostgreSQL
   docker compose exec db pg_dump -U lunaris lunaris_db > backup_$(date +%Y%m%d).sql

   # 备份 Redis
   docker compose exec cache redis-cli BGSAVE
   ```

3. **监控**：
   ```bash
   # 查看容器资源使用
   docker stats
   ```

## 🚨 常见问题

### 容器启动失败

```bash
# 查看详细错误日志
docker compose logs backend

# 检查依赖服务状态
docker compose ps
```

### 数据库连接错误

```bash
# 检查 PostgreSQL 是否就绪
docker compose exec db pg_isready -U lunaris

# 手动测试连接
docker compose exec backend python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine('postgresql+asyncpg://lunaris:password@db:5432/lunaris_db')
print('Connection test passed!')
"
```

### 前端访问 API 失败

```bash
# 检查后端是否运行
docker compose exec frontend curl http://backend:8000/health

# 检查 Nginx 配置
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
```

## 📈 扩展与优化

### 使用外部 PostgreSQL

编辑 `docker-compose.yml`，注释掉 `db` 服务，修改 `DATABASE_URL`：

```yaml
# 在 docker-compose.yml 中
services:
  backend:
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@your-db-host:5432/lunaris_db
```

### 使用外部 Redis

```yaml
services:
  backend:
    environment:
      REDIS_URL: redis://:password@your-redis-host:6379/0
```

### 多实例负载均衡

使用 Docker Swarm 或 Kubernetes：

```bash
# Docker Compose 中运行多个后端副本
docker compose up -d --scale backend=3
```

## 🔐 密钥管理

### 从 Docker Secrets 读取密钥（Swarm 模式）

```yaml
services:
  backend:
    environment:
      JWT_SECRET_FILE: /run/secrets/jwt_secret
    secrets:
      - jwt_secret

secrets:
  jwt_secret:
    external: true
```

## 📚 更多资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 参考](https://docs.docker.com/compose/compose-file/)
- [PostgreSQL Docker 镜像](https://hub.docker.com/_/postgres)
- [Redis Docker 镜像](https://hub.docker.com/_/redis)
