# -*- coding: utf-8 -*-
"""
数据存储模块

注意：TDengine 客户端使用 REST API 模式 (taosrest)
如果不可用，TDEngineClient 将仍然可以被导入，但初始化会失败
"""
from .tdengine_client import TDEngineClient
from .schema import DatabaseSchema, SchemaManager

__all__ = [
    "TDEngineClient",
    "DatabaseSchema",
    "SchemaManager",
    "is_tdengine_available",
    "_tdengine_available",
]

# 延迟检查TDengine是否可用
_tdengine_available = None


def _check_tdengine_available():
    """检查TDengine REST API是否可用（延迟检查）"""
    global _tdengine_available
    if _tdengine_available is None:
        from .tdengine_client import is_tdengine_available as _check
        _tdengine_available = _check()
    return _tdengine_available


def is_tdengine_available():
    """公共接口：检查TDengine是否可用"""
    return _check_tdengine_available()
