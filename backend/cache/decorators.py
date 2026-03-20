# -*- coding: utf-8 -*-
"""
缓存装饰器

提供便捷的函数缓存装饰器
"""
import asyncio
import functools
import hashlib
import json
import inspect
from typing import Any, Callable, Optional, Union, Awaitable, Coroutine
from loguru import logger

from .cache_manager import CacheManager, get_cache_manager


def _generate_key(
    func: Callable, args: tuple, kwargs: dict, key_prefix: Optional[str] = None
) -> str:
    """
    生成缓存键

    Args:
        func: 函数
        args: 位置参数
        kwargs: 关键字参数
        key_prefix: 键前缀

    Returns:
        缓存键
    """
    # 构建键的基础部分
    if key_prefix:
        base = key_prefix
    else:
        base = f"{func.__module__}.{func.__name__}"

    # 序列化参数
    try:
        # 将参数转换为可哈希的字符串
        args_str = json.dumps(args, default=str, sort_keys=True)
        kwargs_str = json.dumps(kwargs, default=str, sort_keys=True)
        params_hash = hashlib.md5(f"{args_str}:{kwargs_str}".encode()).hexdigest()[:8]
        return f"{base}:{params_hash}"
    except Exception:
        # 如果序列化失败，使用参数的字符串表示
        return f"{base}:{str(args)}:{str(kwargs)}"


def cache_result(
    ttl: Optional[int] = None,
    cache_type: str = "default",
    key_prefix: Optional[str] = None,
    ignore_args: Optional[list] = None,
):
    """
    函数结果缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        cache_type: 缓存类型
        key_prefix: 缓存键前缀
        ignore_args: 忽略的参数名列表

    Examples:
        @cache_result(ttl=300, cache_type="quotes")
        async def get_stock_quotes(symbol: str):
            return await fetch_from_source(symbol)

        @cache_result(ttl=600, key_prefix="user:info")
        async def get_user_info(user_id: int):
            return await db.query_user(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取缓存管理器
            cache_manager = await get_cache_manager()

            # 过滤需要忽略的参数
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k not in (ignore_args or [])
            }

            # 生成缓存键
            cache_key = _generate_key(func, args, filtered_kwargs, key_prefix)

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_result

            # 调用原函数
            logger.debug(f"Cache MISS: {cache_key}")
            try:
                result = await func(*args, **kwargs)

                # 存入缓存
                await cache_manager.set(cache_key, result, ttl, cache_type)
                return result

            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函数的支持
            import asyncio

            return asyncio.run(async_wrapper(*args, **kwargs))

        # 判断函数是异步还是同步
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cached(
    key_func: Optional[Callable] = None,
    ttl: Optional[int] = None,
    cache_type: str = "default",
):
    """
    自定义键缓存装饰器

    Args:
        key_func: 自定义键生成函数
        ttl: 缓存过期时间
        cache_type: 缓存类型

    Examples:
        @cached(lambda s: f"stock:{s}", ttl=300)
        async def get_stock_info(symbol: str):
            return await fetch_stock(symbol)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_manager = await get_cache_manager()

            # 使用自定义键函数生成键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_key(func, args, kwargs)

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 调用原函数
            result = await func(*args, **kwargs)

            # 存入缓存
            await cache_manager.set(cache_key, result, ttl, cache_type)
            return result

        return async_wrapper

    return decorator


class CacheGroup:
    """
    缓存组管理器

    用于管理一组相关的缓存，支持批量清除
    """

    def __init__(self, group_name: str):
        """
        初始化缓存组

        Args:
            group_name: 组名称
        """
        self.group_name = group_name

    def _make_key(self, key: str) -> str:
        """生成组内缓存键"""
        return f"{self.group_name}:{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        cache_manager = await get_cache_manager()
        return await cache_manager.get(self._make_key(key), default)

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, cache_type: str = "default"
    ) -> bool:
        """设置缓存"""
        cache_manager = await get_cache_manager()
        return await cache_manager.set(self._make_key(key), value, ttl, cache_type)

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        cache_manager = await get_cache_manager()
        return await cache_manager.delete(self._make_key(key))

    async def clear(self) -> int:
        """清除组内所有缓存"""
        cache_manager = await get_cache_manager()
        return await cache_manager.clear_pattern(f"{self.group_name}:*")

    async def get_or_set(
        self,
        key: str,
        factory: Union[Callable[[], Any], Callable[[], Awaitable[Any]]],
        ttl: Optional[int] = None,
        cache_type: str = "default",
    ) -> Any:
        """获取或设置缓存"""
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        try:
            if inspect.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()

            await self.set(key, value, ttl, cache_type)
            return value

        except Exception as e:
            logger.error(f"Error in cache group factory for key '{key}': {e}")
            raise
