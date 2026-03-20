#!/bin/bash
# -*- coding: utf-8 -*-
# Quant DB 部署脚本
# 用于快速部署和重启服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Quant DB 部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 函数：打印信息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# 函数：打印成功
success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 函数：打印警告
warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 函数：打印错误
error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：显示帮助
show_help() {
    cat << EOF
用法: $0 [命令] [选项]

命令:
    build       构建所有镜像
    rebuild     重新构建并启动所有服务
    up          启动所有服务
    down        停止所有服务
    restart     重启所有服务
    logs        查看服务日志
    status      查看服务状态
    clean       清理容器和卷（危险操作）
    init        初始化数据库和配置

选项:
    -d, --detach    后台运行
    -h, --help      显示帮助信息

示例:
    $0 rebuild           # 重新构建并启动所有服务
    $0 logs backend     # 查看后端服务日志
    $0 status           # 查看所有服务状态

EOF
}

# 函数：构建镜像
build_images() {
    info "构建Docker镜像..."
    docker compose build
    success "镜像构建完成"
}

# 函数：重新构建并启动
rebuild_services() {
    info "停止并删除现有容器..."
    docker compose down

    info "重新构建镜像..."
    docker compose build --no-cache

    info "启动所有服务..."
    docker compose up -d

    success "服务启动完成"
    info "使用 '$0 logs' 查看日志"
    info "使用 '$0 status' 查看服务状态"
}

# 函数：启动服务
start_services() {
    info "启动所有服务..."
    docker compose up -d "$@"
    success "服务启动完成"
}

# 函数：停止服务
stop_services() {
    info "停止所有服务..."
    docker compose down
    success "服务已停止"
}

# 函数：重启服务
restart_services() {
    info "重启所有服务..."
    docker compose restart
    success "服务已重启"
}

# 函数：查看日志
view_logs() {
    local service="$1"
    if [ -z "$service" ]; then
        docker compose logs -f
    else
        docker compose logs -f "$service"
    fi
}

# 函数：查看状态
check_status() {
    info "服务状态:"
    echo ""
    docker compose ps
    echo ""

    # 检查健康状态
    info "健康检查:"
    echo ""

    # 检查后端API
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        success "后端API - 健康"
    else
        error "后端API - 不可访问"
    fi

    # 检查PostgreSQL
    if docker exec quant_postgres pg_isready -U quant_user > /dev/null 2>&1; then
        success "PostgreSQL - 健康"
    else
        error "PostgreSQL - 不可访问"
    fi

    # 检查Redis
    if docker exec quant_redis redis-cli ping > /dev/null 2>&1; then
        success "Redis - 健康"
    else
        error "Redis - 不可访问"
    fi

    # 检查RabbitMQ
    if docker exec quant_rabbitmq rabbitmq-diagnostics -q ping > /dev/null 2>&1; then
        success "RabbitMQ - 健康"
    else
        error "RabbitMQ - 不可访问"
    fi
}

# 函数：清理
clean_up() {
    warn "这将删除所有容器、卷和网络！"
    read -p "确定要继续吗？(yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        info "操作已取消"
        return
    fi

    info "停止并删除所有容器..."
    docker compose down -v

    info "删除未使用的镜像..."
    docker image prune -f

    success "清理完成"
}

# 函数：初始化
init_setup() {
    info "初始化数据库和配置..."

    # 创建必要的目录
    mkdir -p logs data

    # 检查环境变量文件
    if [ ! -f .env ]; then
        warn ".env文件不存在，复制.env.example到.env"
        cp .env.example .env
        info "请编辑.env文件配置环境变量"
    fi

    # 启动基础服务
    info "启动数据库服务..."
    docker compose up -d postgres redis rabbitmq tdengine

    # 等待数据库就绪
    info "等待数据库就绪..."
    sleep 5

    success "初始化完成"
    info "现在可以使用 '$0 up' 启动所有服务"
}

# 主函数
main() {
    case "${1:-}" in
        build)
            build_images
            ;;
        rebuild)
            rebuild_services
            ;;
        up)
            start_services "$@"
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            view_logs "$2"
            ;;
        status)
            check_status
            ;;
        clean)
            clean_up
            ;;
        init)
            init_setup
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            echo -e "${RED}错误: 未知命令 '$1'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
