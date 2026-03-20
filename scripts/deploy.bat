@echo off
REM -*- coding: utf-8 -*-
REM Quant DB 部署脚本 (Windows)
REM 用于快速部署和重启服务

setlocal enabledelayedexpansion

echo ========================================
echo   Quant DB 部署脚本 (Windows)
echo ========================================
echo.

REM 检查Docker是否运行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker未运行，请先启动Docker Desktop
    exit /b 1
)

if "%1"=="" goto show_help
if "%1"=="build" goto build_images
if "%1"=="rebuild" goto rebuild_services
if "%1"=="up" goto start_services
if "%1"=="down" goto stop_services
if "%1"=="restart" goto restart_services
if "%1"=="logs" goto view_logs
if "%1"=="status" goto check_status
if "%1"=="clean" goto clean_up
if "%1"=="init" goto init_setup
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

echo [ERROR] 未知命令: %1
goto show_help

:show_help
echo 用法: %~nx0 [命令] [选项]
echo.
echo 命令:
echo     build       构建所有镜像
echo     rebuild     重新构建并启动所有服务
echo     up          启动所有服务
echo     down        停止所有服务
echo     restart     重启所有服务
echo     logs        查看服务日志
echo     status      查看服务状态
echo     clean       清理容器和卷（危险操作）
echo     init        初始化数据库和配置
echo.
echo 示例:
echo     %~nx0 rebuild           # 重新构建并启动所有服务
echo     %~nx0 logs backend     # 查看后端服务日志
echo     %~nx0 status           # 查看所有服务状态
echo.
goto end

:build_images
echo [INFO] 构建Docker镜像...
docker compose build
if %errorlevel% equ 0 (
    echo [SUCCESS] 镜像构建完成
) else (
    echo [ERROR] 镜像构建失败
    exit /b 1
)
goto end

:rebuild_services
echo [INFO] 停止并删除现有容器...
docker compose down

echo [INFO] 重新构建镜像...
docker compose build --no-cache

echo [INFO] 启动所有服务...
docker compose up -d

if %errorlevel% equ 0 (
    echo [SUCCESS] 服务启动完成
    echo [INFO] 使用 '%~nx0 logs' 查看日志
    echo [INFO] 使用 '%~nx0 status' 查看服务状态
) else (
    echo [ERROR] 服务启动失败
    exit /b 1
)
goto end

:start_services
echo [INFO] 启动所有服务...
docker compose up -d
if %errorlevel% equ 0 (
    echo [SUCCESS] 服务启动完成
) else (
    echo [ERROR] 服务启动失败
    exit /b 1
)
goto end

:stop_services
echo [INFO] 停止所有服务...
docker compose down
echo [SUCCESS] 服务已停止
goto end

:restart_services
echo [INFO] 重启所有服务...
docker compose restart
echo [SUCCESS] 服务已重启
goto end

:view_logs
if "%2"=="" (
    docker compose logs -f
) else (
    docker compose logs -f %2
)
goto end

:check_status
echo [INFO] 服务状态:
echo.
docker compose ps
echo.

echo [INFO] 健康检查:
echo.

REM 检查后端API
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] 后端API - 健康
) else (
    echo [ERROR] 后端API - 不可访问
)

REM 检查PostgreSQL
docker exec quant_postgres pg_isready -U quant_user >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] PostgreSQL - 健康
) else (
    echo [ERROR] PostgreSQL - 不可访问
)

REM 检查Redis
docker exec quant_redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Redis - 健康
) else (
    echo [ERROR] Redis - 不可访问
)

REM 检查RabbitMQ
docker exec quant_rabbitmq rabbitmq-diagnostics -q ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] RabbitMQ - 健康
) else (
    echo [ERROR] RabbitMQ - 不可访问
)
goto end

:clean_up
echo [WARN] 这将删除所有容器、卷和网络！
set /p confirm="确定要继续吗？(yes/no): "
if not "%confirm%"=="yes" (
    echo [INFO] 操作已取消
    goto end
)

echo [INFO] 停止并删除所有容器...
docker compose down -v

echo [INFO] 删除未使用的镜像...
docker image prune -f

echo [SUCCESS] 清理完成
goto end

:init_setup
echo [INFO] 初始化数据库和配置...

REM 创建必要的目录
if not exist "logs" mkdir logs
if not exist "data" mkdir data

REM 检查环境变量文件
if not exist ".env" (
    echo [WARN] .env文件不存在，复制.env.example到.env
    copy .env.example .env
    echo [INFO] 请编辑.env文件配置环境变量
)

echo [INFO] 启动数据库服务...
docker compose up -d postgres redis rabbitmq tdengine

echo [INFO] 等待数据库就绪...
timeout /t 5 /nobreak >nul

echo [SUCCESS] 初始化完成
echo [INFO] 现在可以使用 '%~nx0 up' 启动所有服务
goto end

:end
endlocal
