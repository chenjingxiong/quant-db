#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目问题验证脚本
用于诊断和验证Quant_DB项目中的潜在问题
"""
import os
import sys
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path("/root/projects/Quant_DB")

def check_frontend_dist():
    """检查前端构建产物是否存在"""
    print("\n=== 检查1: 前端构建产物 ===")
    dist_path = PROJECT_ROOT / "frontend" / "dist"
    if dist_path.exists():
        print(f"✓ 前端dist目录存在: {dist_path}")
        return True
    else:
        print(f"✗ 前端dist目录不存在: {dist_path}")
        print("  影响: docker-compose启动时会失败，nginx无法提供静态文件")
        return False

def check_dependencies():
    """检查依赖包是否安装"""
    print("\n=== 检查2: Python依赖包 ===")
    try:
        import taos
        print("✓ taos (taospy) 已安装")
        taos_ok = True
    except ImportError:
        print("✗ taos (taospy) 未安装")
        taos_ok = False
    
    try:
        import pytdx
        print("✓ pytdx 已安装")
        pytdx_ok = True
    except ImportError:
        print("✗ pytdx 未安装")
        pytdx_ok = False
    
    try:
        import fastapi
        print("✓ fastapi 已安装")
        fastapi_ok = True
    except ImportError:
        print("✗ fastapi 未安装")
        fastapi_ok = False
    
    if not (taos_ok and pytdx_ok and fastapi_ok):
        print("  影响: 后端服务无法启动")
        return False
    return True

def check_python_version():
    """检查Python版本"""
    print("\n=== 检查3: Python版本 ===")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    if version >= (3, 9):
        print("✓ Python版本符合要求 (3.9+)")
        return True
    else:
        print("✗ Python版本过低，需要3.9+")
        return False

def check_docker_config():
    """检查Docker配置"""
    print("\n=== 检查4: Docker配置 ===")
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        print("✗ docker-compose.yml 不存在")
        return False
    
    # 检查frontend volume配置
    with open(compose_file, 'r') as f:
        content = f.read()
        if "./frontend/dist" in content:
            print("✓ docker-compose.yml 引用了 frontend/dist")
        else:
            print("✗ docker-compose.yml 未引用 frontend/dist")
    
    return True

def check_code_issues():
    """检查代码中的潜在问题"""
    print("\n=== 检查5: 代码潜在问题 ===")
    
    # 检查1: asyncio.get_event_loop() 使用
    files_with_issue = []
    for py_file in PROJECT_ROOT.glob("backend/**/*.py"):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                if "asyncio.get_event_loop()" in content:
                    files_with_issue.append(str(py_file.relative_to(PROJECT_ROOT)))
        except:
            pass
    
    if files_with_issue:
        print(f"✗ 发现 {len(files_with_issue)} 个文件使用了已弃用的 asyncio.get_event_loop():")
        for f in files_with_issue:
            print(f"  - {f}")
    else:
        print("✓ 未发现 asyncio.get_event_loop() 使用")
    
    # 检查2: 全局变量使用
    app_file = PROJECT_ROOT / "backend" / "api" / "app.py"
    if app_file.exists():
        with open(app_file, 'r') as f:
            content = f.read()
            if "td_client: TDEngineClient = None" in content:
                print("✓ 发现全局变量 td_client，可能有并发问题")
    
    return True

def main():
    print("=" * 60)
    print("Quant_DB 项目问题诊断")
    print("=" * 60)
    
    results = {
        "frontend_dist": check_frontend_dist(),
        "dependencies": check_dependencies(),
        "python_version": check_python_version(),
        "docker_config": check_docker_config(),
        "code_issues": check_code_issues(),
    }
    
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    critical_issues = []
    warnings = []
    
    if not results["frontend_dist"]:
        critical_issues.append("前端构建产物缺失")
    if not results["dependencies"]:
        critical_issues.append("Python依赖未安装")
    
    if critical_issues:
        print("\n严重问题:")
        for issue in critical_issues:
            print(f"  ✗ {issue}")
    
    if warnings:
        print("\n警告:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
    
    if not critical_issues and not warnings:
        print("\n✓ 未发现严重问题")
    
    return 0 if not critical_issues else 1

if __name__ == "__main__":
    sys.exit(main())