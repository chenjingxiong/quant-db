# -*- coding: utf-8 -*-
"""
量化金融数据采集系统 - 主入口

启动命令:
    python backend/main.py
"""
import asyncio
import sys
import os

# 添加项目根目录到路径（支持从 backend/main.py 运行）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.api.app import app
from backend.config import get_settings
import uvicorn


def main():
    """主函数"""
    settings = get_settings()

    # 配置日志
    from backend.utils.logger import setup_logger
    setup_logger(settings.log_level, settings.log_dir)

    # 启动API服务
    uvicorn.run(
        "backend.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_workers == 1 and "--reload" in sys.argv,
        workers=settings.api_workers if "--reload" not in sys.argv else 1,
        access_log=True,
    )


if __name__ == "__main__":
    main()
