# -*- coding: utf-8 -*-
"""
缓存模块

提供Redis缓存功能，支持数据缓存、会话存储、分布式锁等
"""
from .redis_client import RedisClient, get_redis_client
from .cache_manager import CacheManager, get_cache_manager
from .decorators import cache_result, cached

__all__ = [
    "RedisClient",
    "get_redis_client",
    "CacheManager",
    "get_cache_manager",
    "cache_result",
    "cached",
]
