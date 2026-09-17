# ============================================================
# Lunaris 前端 Dockerfile
# 多阶段构建：Node 构建 → Nginx 静态托管 + API 反向代理
#
# 构建命令：
#   docker build -t lunaris-frontend:latest .
# ============================================================

FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖清单
COPY package.json package-lock.json ./

# 安装依赖（只装生产依赖）
RUN npm ci --production=false

# 复制源码
COPY . .

# 构建 Vite 项目（项目配置输出到 /electron/renderer）
RUN npm run build

# ============================================================
# 运行阶段：Nginx 托管静态文件 + 反向代理 API
# ============================================================
FROM nginx:latest

# 复制构建产物
COPY --from=builder /electron/renderer /usr/share/nginx/html

# 复制 Nginx 配置（实现 SPA 路由 + API 反向代理）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
