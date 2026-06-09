@echo off
REM -*- coding: utf-8 -*-
REM Quant DB 备份脚本 (Windows)
REM 用于备份PostgreSQL数据库和配置文件

setlocal enabledelayedexpansion

REM 配置
set "BACKUP_DIR=%BACKUP_DIR%.\backups"
set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

if "%1"=="" goto all_backup
if "%1"=="all" goto all_backup
if "%1"=="postgres" goto backup_postgres
if "%1"=="redis" goto backup_redis
if "%1"=="config" goto backup_config
if "%1"=="cleanup" goto cleanup_old
if "%1"=="list" goto list_backups
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

echo [ERROR] 未知命令: %1
goto show_help

:show_help
echo 用法: %~nx0 [命令] [选项]
echo.
echo 命令:
echo     all             备份所有数据（默认）
echo     postgres        仅备份PostgreSQL
echo     redis           仅备份Redis
echo     config          仅备份配置文件
echo     cleanup         清理旧备份
echo     list            列出所有备份
echo.
echo 示例:
echo     %~nx0              # 备份所有
echo     %~nx0 postgres     # 仅备份PostgreSQL
echo     %~nx0 list         # 列出备份
echo.
goto end

:all_backup
echo [INFO] 备份所有数据...
call :backup_postgres
call :backup_redis
call :backup_config
goto end

:backup_postgres
echo [INFO] 备份PostgreSQL数据库...

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
set "backup_file=%BACKUP_DIR%\postgres_%TIMESTAMP%.sql.gz"

docker exec quant_postgres pg_dump -U quant_user quant_db | docker exec -i quant_postgres gzip > "%backup_file%"

if %errorlevel% equ 0 (
    echo [SUCCESS] PostgreSQL备份完成: %backup_file%
    dir "%backup_file%"
) else (
    echo [ERROR] PostgreSQL备份失败
)
goto end

:backup_redis
echo [INFO] 备份Redis数据...

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
set "backup_file=%BACKUP_DIR%\redis_%TIMESTAMP%.rdb"

REM 触发Redis保存
docker exec quant_redis redis-cli BGSAVE

REM 等待保存完成
timeout /t 2 /nobreak >nul

REM 复制RDB文件
docker cp quant_redis:/data/dump.rdb "%backup_file%"

if %errorlevel% equ 0 (
    echo [SUCCESS] Redis备份完成: %backup_file%
    dir "%backup_file%"
) else (
    echo [ERROR] Redis备份失败
)
goto end

:backup_config
echo [INFO] 备份配置文件...

set "config_dir=%BACKUP_DIR%\config_%TIMESTAMP%"
mkdir "%config_dir%"

if exist ".env" copy ".env" "%config_dir%\" >nul 2>&1
if exist "docker" xcopy /E /I "docker" "%config_dir%\docker\" >nul 2>&1
if exist "docker-compose.yml" copy "docker-compose.yml" "%config_dir%\" >nul 2>&1
if exist "docker-compose.dev.yml" copy "docker-compose.dev.yml" "%config_dir%\" >nul 2>&1
if exist "docker-compose.prod.yml" copy "docker-compose.prod.yml" "%config_dir%\" >nul 2>&1

echo [SUCCESS] 配置文件备份完成: %config_dir%
goto end

:cleanup_old
echo [INFO] 清理7天前的旧备份...
REM Windows的forfiles命令用于删除旧文件
forfiles /P "%BACKUP_DIR%" /M postgres_*.sql.gz /D -7 /C "cmd /c del @path" 2>nul
forfiles /P "%BACKUP_DIR%" /M redis_*.rdb /D -7 /C "cmd /c del @path" 2>nul
echo [SUCCESS] 旧备份清理完成
goto end

:list_backups
echo [INFO] 可用的备份文件:
echo.
echo PostgreSQL:
dir /B /O-D "%BACK_DIR%\postgres_*.sql.gz" 2>nul || echo   无备份
echo.
echo Redis:
dir /B /O-D "%BACK_DIR%\redis_*.rdb" 2>nul || echo   无备份
echo.
echo 配置:
dir /B /O-D "%BACK_DIR%\config_*" 2>nul || echo   无备份
goto end

:end
endlocal
