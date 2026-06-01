# -*- coding: utf-8 -*-
"""
限流中间件

提供基于IP、用户、API Key的请求频率限制功能
"""
from typing import Optional, Dict, Callable
from fastapi import Request, HTTPException, status
from loguru import logger
import time
from collections import defaultdict
from asyncio import Lock

from ..cache import get_cache_manager


class RateLimiter:
    """限流器"""

    def __init__(
        self,
        default_limit: int = 100,  # 默认请求次数
        default_window: int = 60,  # 默认时间窗口（秒）
    ):
        """
        初始化限流器

        Args:
            default_limit: 默认请求次数限制
            default_window: 默认时间窗口（秒）
        """
        self.default_limit = default_limit
        self.default_window = default_window
        self._local_store: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
        self.cache_manager = None

    async def _get_cache_manager(self):
        """获取缓存管理器"""
        if self.cache_manager is None:
            self.cache_manager = get_cache_manager()
        return self.cache_manager

    async def is_allowed(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> tuple[bool, Dict]:
        """
        检查是否允许请求

        Args:
            key: 限流键（如用户ID、IP地址等）
            limit: 请求次数限制
            window: 时间窗口（秒）

        Returns:
            (是否允许, 限流信息)
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        current_time = int(time.time())
        window_start = current_time - window

        # 先尝试从Redis获取
        cache_manager = await self._get_cache_manager()
        cache_key = f"ratelimit:{key}"

        try:
            # 使用Redis sorted set存储请求时间戳
            await cache_manager._get_client().zremrangebyscore(
                cache_key,
                0,
                window_start
            )

            # 获取当前窗口内的请求计数
            count = await cache_manager._get_client().zcard(cache_key)

            if count >= limit:
                ttl = await cache_manager._get_client().ttl(cache_key)
                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": ttl or window
                }

            # 记录本次请求
            await cache_manager._get_client().zadd(
                cache_key,
                {str(current_time): current_time}
            )
            await cache_manager._get_client().expire(cache_key, window)

            # 计算剩余配额
            remaining = max(0, limit - count - 1)
            return True, {
                "limit": limit,
                "remaining": remaining,
                "reset": window
            }

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # 降级到本地存储
            async with self._lock:
                timestamps = self._local_store[key]
                # 移除过期时间戳
                timestamps[:] = [t for t in timestamps if t > window_start]

                if len(timestamps) >= limit:
                    return False, {
                        "limit": limit,
                        "remaining": 0,
                        "reset": window
                    }

                timestamps.append(current_time)
                remaining = max(0, limit - len(timestamps))
                return True, {
                    "limit": limit,
                    "remaining": remaining,
                    "reset": window
                }


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class RateLimitConfig:
    """限流配置"""

    # API端点限流配置
    API_LIMITS = {
        "default": (100, 60),  # 100次/分钟
        "health": (1000, 60),  # 1000次/分钟
        "login": (5, 60),  # 5次/分钟
        "register": (3, 3600),  # 3次/小时
        "stock:read": (1000, 60),  # 1000次/分钟
        "stock:write": (100, 60),  # 100次/分钟
        "backtest": (10, 60),  # 10次/分钟
    }

    # 用户级别限流配置
    USER_LIMITS = {
        "guest": (100, 60),
        "user": (1000, 60),
        "trader": (5000, 60),
        "admin": (10000, 60),
    }

    @classmethod
    def get_api_limit(cls, endpoint: str) -> tuple[int, int]:
        """获取API端点限流配置"""
        # 精确匹配
        if endpoint in cls.API_LIMITS:
            return cls.API_LIMITS[endpoint]

        # 前缀匹配
        for key, config in cls.API_LIMITS.items():
            if endpoint.startswith(key):
                return config

        # 默认配置
        return cls.API_LIMITS["default"]

    @classmethod
    def get_user_limit(cls, role: str) -> tuple[int, int]:
        """获取用户级别限流配置"""
        return cls.USER_LIMITS.get(role, cls.USER_LIMITS["guest"])


async def check_rate_limit(
    request: Request,
    key: str,
    limit: Optional[int] = None,
    window: Optional[int] = None
) -> None:
    """
    检查限流

    Args:
        request: FastAPI请求对象
        key: 限流键
        limit: 限制次数
        window: 时间窗口

    Raises:
        HTTPException: 如果超过限流
    """
    rate_limiter = get_rate_limiter()
    allowed, info = await rate_limiter.is_allowed(key, limit, window)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": info["limit"],
                "window": info["reset"],
                "retry_after": info.get("reset", 60)
            },
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(info.get("reset", 60))
            }
        )

    # 添加限流响应头到请求状态（供后续中间件使用）
    request.state.rate_limit_info = info


def get_client_identifier(request: Request) -> str:
    """获取客户端标识符"""
    # 1. 优先使用用户ID（如果已认证）
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.get('sub')}"

    # 2. 使用API Key前缀
    api_key = request.headers.get("X-API-Key", "")
    if api_key and api_key.startswith("qtk_"):
        parts = api_key.split("_")
        if len(parts) >= 2:
            return f"apikey:{parts[1]}"

    # 3. 使用IP地址
    # 注意：在反向代理后面需要从header获取真实IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"

    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def get_rate_limit_key(request: Request) -> str:
    """
    获取限流键

    结合用户信息和请求路径生成唯一的限流键
    """
    identifier = get_client_identifier(request)
    path = request.url.path.lstrip("/")
    return f"{identifier}:{path}"
