# -*- coding: utf-8 -*-
"""
异步兼容性模块

提供跨版本兼容的异步事件循环获取函数
"""
import asyncio
import sys


def get_event_loop():
    """
    获取事件循环（兼容Python 3.10+）
    
    在Python 3.10+中，asyncio.get_event_loop()已被弃用，
    应使用asyncio.get_running_loop()或asyncio.new_event_loop()
    """
    try:
        # 尝试获取运行中的循环
        return asyncio.get_running_loop()
    except RuntimeError:
        # 没有运行中的循环，创建新的
        return asyncio.new_event_loop()


__all__ = ['get_event_loop']
