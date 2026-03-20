# -*- coding: utf-8 -*-
"""
缓存管理器

提供统一的缓存管理接口，支持多种缓存策略
"""
from typing import Any, Optional, Dict, List, Callable, Awaitable
from loguru import logger
from enum import Enum

from .redis_client import RedisClient, get_redis_client


class CacheStrategy(Enum):
    """缓存策略"""

    LRU = "lru"  # 最近最少使用
    TTL = "ttl"  # 基于时间
    WRITE_THROUGH = "write_through"  # 写透
    WRITE_BACK = "write_back"  # 写回


class CacheManager:
    """缓存管理器"""

    # 默认缓存时长配置（秒）
    DEFAULT_TTL_CONFIG = {
        "quotes": 5,  # 实时行情：5秒
        "bars": 3600,  # K线数据：1小时
        "stock_list": 86400,  # 股票列表：1天
        "indicators": 1800,  # 技术指标：30分钟
        "user_session": 86400,  # 用户会话：24小时
        "screener_result": 600,  # 选股结果：10分钟
        "default": 300,  # 默认：5分钟
    }

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        初始化缓存管理器

        Args:
            redis_client: Redis客户端，如果为None则使用全局实例
        """
        self.redis_client = redis_client

    async def _get_client(self) -> RedisClient:
        """获取Redis客户端"""
        if self.redis_client is None:
            return await get_redis_client()
        return self.redis_client

    def get_ttl(self, cache_type: str) -> int:
        """
        获取缓存类型对应的默认TTL

        Args:
            cache_type: 缓存类型

        Returns:
            TTL（秒）
        """
        return self.DEFAULT_TTL_CONFIG.get(cache_type, self.DEFAULT_TTL_CONFIG["default"])

    async def get(
        self, key: str, default: Optional[Any] = None
    ) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        client = await self._get_client()
        return await client.cache_get(key, default)

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, cache_type: str = "default"
    ) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），为None时使用cache_type的默认值
            cache_type: 缓存类型

        Returns:
            是否设置成功
        """
        if ttl is None:
            ttl = self.get_ttl(cache_type)

        client = await self._get_client()
        return await client.cache_set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        client = await self._get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        client = await self._get_client()
        return await client.exists(key)

    async def clear_pattern(self, pattern: str) -> int:
        """
        批量清除匹配模式的缓存

        Args:
            pattern: 键模式（如 "stock:*"）

        Returns:
            清除的缓存数量
        """
        client = await self._get_client()
        return await client.clear_pattern(pattern)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]] | Callable[[], Any],
        ttl: Optional[int] = None,
        cache_type: str = "default",
    ) -> Any:
        """
        获取缓存，如果不存在则通过factory创建并缓存

        Args:
            key: 缓存键
            factory: 数据工厂函数
            ttl: 过期时间
            cache_type: 缓存类型

        Returns:
            缓存值
        """
        # 尝试从缓存获取
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # 调用工厂函数创建数据
        try:
            # 检查是否是可调用对象
            if callable(factory):
                value = factory()
                # 如果返回值是协程，则需要await
                if isinstance(value, Awaitable):
                    value = await value
            elif isinstance(factory, Awaitable):
                value = await factory
            else:
                value = factory

            # 存入缓存
            await self.set(key, value, ttl, cache_type)
            return value

        except Exception as e:
            logger.error(f"Error in cache factory for key '{key}': {e}")
            raise

    async def refresh(self, key: str, cache_type: str = "default") -> bool:
        """
        刷新缓存过期时间

        Args:
            key: 缓存键
            cache_type: 缓存类型

        Returns:
            是否刷新成功
        """
        client = await self._get_client()
        ttl = self.get_ttl(cache_type)
        return await client.expire(key, ttl)

    # ===========================
    # 批量操作
    # ===========================

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取缓存

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典
        """
        client = await self._get_client()
        result = {}

        for key in keys:
            value = await client.cache_get(key)
            if value is not None:
                result[key] = value

        return result

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None, cache_type: str = "default"
    ) -> int:
        """
        批量设置缓存

        Args:
            mapping: 键值对字典
            ttl: 过期时间
            cache_type: 缓存类型

        Returns:
            成功设置的数量
        """
        if ttl is None:
            ttl = self.get_ttl(cache_type)

        client = await self._get_client()
        success_count = 0

        for key, value in mapping.items():
            if await client.cache_set(key, value, ttl):
                success_count += 1

        return success_count

    async def delete_many(self, keys: List[str]) -> int:
        """
        批量删除缓存

        Args:
            keys: 缓存键列表

        Returns:
            成功删除的数量
        """
        client = await self._get_client()
        success_count = 0

        for key in keys:
            if await client.delete(key):
                success_count += 1

        return success_count

    # ===========================
    # 缓存预热
    # ===========================

    async def warm_up(
        self, data: Dict[str, Any], cache_type: str = "default"
    ) -> int:
        """
        缓存预热

        Args:
            data: 预热数据字典
            cache_type: 缓存类型

        Returns:
            成功缓存的数量
        """
        return await self.set_many(data, cache_type=cache_type)

    # ===========================
    # 缓存统计
    # ===========================

    async def get_stats(self, pattern: str = "*") -> Dict[str, int]:
        """
        获取缓存统计信息

        Args:
            pattern: 键模式

        Returns:
            统计信息
        """
        client = await self._get_client()

        count = 0
        total_memory = 0

        try:
            async for key in client.client.scan_iter(match=pattern):
                count += 1
                # 获取内存使用
                memory = await client.client.memory_usage(key)
                if memory:
                    total_memory += memory

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")

        return {
            "key_count": count,
            "total_memory_bytes": total_memory,
            "total_memory_mb": round(total_memory / 1024 / 1024, 2),
        }


# ===========================
# 全局缓存管理器
# ===========================

_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
