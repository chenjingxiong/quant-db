# -*- coding: utf-8 -*-
"""
API模块 - 使用延迟导入避免循环依赖
"""


def __getattr__(name):
    if name == "create_app":
        from .app import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
