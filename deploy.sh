#!/bin/bash
# ============================================================
# Lunaris Docker 一键部署脚本
# 用法: bash deploy.sh [start|stop|restart|logs|shell]
# ============================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    log_success "Docker 已安装: $(docker --version)"
}

# 检查 Docker Compose
check_docker_compose() {
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    log_success "Docker Compose 已安装: $(docker compose version)"
}

# 检查环境配置
check_env() {
    if [ ! -f ".env" ]; then
        log_warn ".env 文件不存在，正在从 .env.docker 复制..."
        cp .env.docker .env
        log_warn "请编辑 .env 文件并填入真实的密钥，然后重新运行此脚本"
        exit 1
    fi
    log_success ".env 文件已存在"
}

# 启动服务
start_services() {
    log_info "启动 Lunaris 容器..."
    docker compose up -d --build
    log_success "容器启动中..."

    # 等待服务就绪
    log_info "等待服务就绪（约 30 秒）..."
    sleep 30

    log_info "检查服务状态..."
    docker compose ps

    log_success "✨ 启动完成！"
    echo ""
    echo "📍 访问地址："
    echo "   前端: ${BLUE}http://localhost:3000${NC}"
    echo "   API:  ${BLUE}http://localhost:8001${NC}"
    echo ""
    echo "🔧 查看日志:"
    echo "   bash deploy.sh logs"
    echo ""
}

# 停止服务
stop_services() {
    log_info "停止 Lunaris 容器..."
    docker compose down
    log_success "容器已停止"
}

# 重启服务
restart_services() {
    log_info "重启 Lunaris 容器..."
    docker compose restart
    log_success "容器已重启"
}

# 查看日志
view_logs() {
    log_info "显示服务日志（Ctrl+C 退出）..."
    docker compose logs -f
}

# 进入容器 Shell
shell_service() {
    local service="${1:-backend}"
    log_info "进入 ${service} 容器..."
    docker compose exec ${service} bash
}

# 初始化数据库
init_db() {
    log_info "初始化数据库..."
    docker compose exec -T backend alembic -c alembic/alembic.ini upgrade head
    log_success "数据库迁移完成"

    log_info "初始化演示数据..."
    docker compose exec -T backend python scripts/init_souls.py
    docker compose exec -T backend python scripts/init_stickers.py
    log_success "演示数据初始化完成"
}

# 备份数据库
backup_db() {
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    log_info "备份数据库到 ${backup_file}..."
    docker compose exec -T db pg_dump -U lunaris lunaris_db > "${backup_file}"
    log_success "备份完成: ${backup_file}"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查容器状态
    docker compose ps

    # 检查后端健康
    log_info "检查后端 API..."
    if curl -s http://localhost:8001/health > /dev/null; then
        log_success "后端 API 正常"
    else
        log_error "后端 API 无响应"
    fi

    # 检查前端
    log_info "检查前端..."
    if curl -s http://localhost:3000 > /dev/null; then
        log_success "前端正常"
    else
        log_error "前端无响应"
    fi

    # 检查数据库
    log_info "检查数据库..."
    if docker compose exec -T db pg_isready -U lunaris > /dev/null; then
        log_success "数据库正常"
    else
        log_error "数据库无响应"
    fi
}

# 清理所有数据（危险操作）
cleanup() {
    log_warn "⚠️  即将删除所有容器、镜像和卷（包括数据库数据）！"
    read -p "确认删除？(yes/no): " confirm

    if [ "${confirm}" = "yes" ]; then
        log_info "清理中..."
        docker compose down -v
        log_success "清理完成"
    else
        log_info "已取消"
    fi
}

# 主函数
main() {
    local cmd="${1:-help}"

    check_docker
    check_docker_compose

    case "${cmd}" in
        start)
            check_env
            start_services
            init_db
            health_check
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            view_logs
            ;;
        shell)
            shell_service "${2:-backend}"
            ;;
        db-init)
            init_db
            ;;
        backup)
            backup_db
            ;;
        health)
            health_check
            ;;
        clean)
            cleanup
            ;;
        *)
            cat << 'EOF'
使用方法: bash deploy.sh <命令>

命令列表：
  start       启动所有服务（包括初始化数据库）
  stop        停止所有服务
  restart     重启所有服务
  logs        查看实时日志（Ctrl+C 退出）
  shell       进入容器 shell（默认 backend，可指定 db/cache/frontend）
  db-init     初始化数据库和演示数据
  backup      备份 PostgreSQL 数据库
  health      执行健康检查
  clean       删除所有容器、镜像和卷（⚠️ 危险！）

示例：
  bash deploy.sh start
  bash deploy.sh logs
  bash deploy.sh shell db
  bash deploy.sh backup
EOF
            exit 1
            ;;
    esac
}

main "$@"
