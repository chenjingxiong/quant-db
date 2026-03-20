#!/bin/bash
# -*- coding: utf-8 -*-
# Quant DB 备份脚本
# 用于备份PostgreSQL数据库和配置文件

set -e

# 配置
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=7

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 函数：备份PostgreSQL
backup_postgres() {
    info "备份PostgreSQL数据库..."

    local backup_file="$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"

    docker exec quant_postgres pg_dump -U quant_user quant_db | gzip > "$backup_file"

    if [ $? -eq 0 ]; then
        success "PostgreSQL备份完成: $backup_file"
        ls -lh "$backup_file"
    else
        error "PostgreSQL备份失败"
        return 1
    fi
}

# 函数：备份Redis
backup_redis() {
    info "备份Redis数据..."

    local backup_file="$BACKUP_DIR/redis_$TIMESTAMP.rdb"

    # 触发Redis保存
    docker exec quant_redis redis-cli BGSAVE

    # 等待保存完成
    sleep 2

    # 复制RDB文件
    docker cp quant_redis:/data/dump.rdb "$backup_file"

    if [ $? -eq 0 ]; then
        success "Redis备份完成: $backup_file"
        ls -lh "$backup_file"
    else
        error "Redis备份失败"
        return 1
    fi
}

# 函数：备份配置文件
backup_config() {
    info "备份配置文件..."

    local config_dir="$BACKUP_DIR/config_$TIMESTAMP"
    mkdir -p "$config_dir"

    cp .env "$config_dir/" 2>/dev/null || warn ".env文件不存在"
    cp -r docker "$config_dir/" 2>/dev/null || true
    cp docker-compose*.yml "$config_dir/" 2>/dev/null || true

    success "配置文件备份完成: $config_dir"
}

# 函数：备份TDengine
backup_tdengine() {
    info "备份TDengine数据库..."

    local backup_file="$BACKUP_DIR/tdengine_$TIMESTAMP.sql"

    docker exec quant_tdengine taos -s "SHOW DATABASES;" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        docker exec quant_tdengine taos -s "SCRIPT_PLACEHOLDER" > "$backup_file" 2>/dev/null || true
        success "TDengine备份完成: $backup_file"
    else
        warn "TDengine不可用，跳过备份"
    fi
}

# 函数：清理旧备份
cleanup_old_backups() {
    info "清理 $RETENTION_DAYS 天前的旧备份..."

    find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "tdengine_*.sql" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type d -name "config_*" -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true

    success "旧备份清理完成"
}

# 函数：恢复PostgreSQL
restore_postgres() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        error "请指定备份文件"
        echo "用法: $0 restore-postgres <backup_file>"
        return 1
    fi

    if [ ! -f "$backup_file" ]; then
        error "备份文件不存在: $backup_file"
        return 1
    fi

    info "恢复PostgreSQL数据库从: $backup_file"

    warn "这将覆盖现有数据库！"
    read -p "确定要继续吗？(yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        info "操作已取消"
        return 0
    fi

    # 删除并重建数据库
    docker exec -i quant_postgres psql -U quant_user -c "DROP DATABASE IF EXISTS quant_db;"
    docker exec -i quant_postgres psql -U quant_user -c "CREATE DATABASE quant_db;"

    # 恢复数据
    gunzip -c "$backup_file" | docker exec -i quant_postgres psql -U quant_user -d quant_db

    success "数据库恢复完成"
}

# 函数：列出备份
list_backups() {
    info "可用的备份文件:"
    echo ""
    echo "PostgreSQL:"
    ls -lht "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null || echo "  无备份"
    echo ""
    echo "Redis:"
    ls -lht "$BACKUP_DIR"/redis_*.rdb 2>/dev/null || echo "  无备份"
    echo ""
    echo "TDengine:"
    ls -lht "$BACKUP_DIR"/tdengine_*.sql 2>/dev/null || echo "  无备份"
    echo ""
    echo "配置:"
    ls -lht "$BACKUP_DIR"/config_* 2>/dev/null || echo "  无备份"
}

# 显示帮助
show_help() {
    cat << EOF
用法: $0 [命令] [选项]

命令:
    all             备份所有数据（默认）
    postgres        仅备份PostgreSQL
    redis           仅备份Redis
    tdengine        仅备份TDengine
    config          仅备份配置文件
    cleanup         清理旧备份
    restore-postgres <file>   恢复PostgreSQL
    list            列出所有备份

选项:
    -h, --help      显示帮助信息

环境变量:
    BACKUP_DIR      备份目录（默认: ./backups）
    RETENTION_DAYS  保留天数（默认: 7）

示例:
    $0                      # 备份所有
    $0 postgres             # 仅备份PostgreSQL
    $0 restore-postgres ./backups/postgres_20240101_120000.sql.gz
    $0 list                 # 列出备份

EOF
}

# 主函数
main() {
    case "${1:-all}" in
        all)
            backup_postgres
            backup_redis
            backup_tdengine
            backup_config
            cleanup_old_backups
            ;;
        postgres)
            backup_postgres
            ;;
        redis)
            backup_redis
            ;;
        tdengine)
            backup_tdengine
            ;;
        config)
            backup_config
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        restore-postgres)
            restore_postgres "$2"
            ;;
        list)
            list_backups
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
