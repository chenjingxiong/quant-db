# -*- coding: utf-8 -*-
"""
中间件模块

提供认证、限流、CORS等中间件功能
"""
from .auth import (
    AuthMiddleware,
    get_auth_middleware,
    require_auth,
    require_permission,
    require_role,
    require_admin,
    require_trader,
)
from .rate_limit import (
    RateLimiter,
    get_rate_limiter,
    RateLimitConfig,
    check_rate_limit,
    get_client_identifier,
    get_rate_limit_key,
)

__all__ = [
    "AuthMiddleware",
    "get_auth_middleware",
    "require_auth",
    "require_permission",
    "require_role",
    "require_admin",
    "require_trader",
    "RateLimiter",
    "get_rate_limiter",
    "RateLimitConfig",
    "check_rate_limit",
    "get_client_identifier",
    "get_rate_limit_key",
]
