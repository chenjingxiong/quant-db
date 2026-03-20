# -*- coding: utf-8 -*-
"""
认证中间件

提供JWT认证、API Key认证、权限验证等功能
"""
from typing import Optional, Callable, List
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from ..services.auth import JWTHandler, get_jwt_handler, APIKeyHandler, get_apikey_handler
from ..services.auth.permissions import Permission, Role, has_permission
from ..cache import get_cache_manager


security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """认证中间件"""

    def __init__(self):
        self.jwt_handler: Optional[JWTHandler] = None
        self.apikey_handler: Optional[APIKeyHandler] = None
        self.cache_manager = None

    async def _get_handlers(self):
        """获取处理器实例（延迟初始化）"""
        if self.jwt_handler is None:
            self.jwt_handler = get_jwt_handler()
        if self.apikey_handler is None:
            self.apikey_handler = get_apikey_handler()
        if self.cache_manager is None:
            self.cache_manager = get_cache_manager()

    async def authenticate(
        self,
        request: Request,
        required_permissions: Optional[List[Permission]] = None
    ) -> Optional[dict]:
        """
        认证请求并验证权限

        Args:
            request: FastAPI请求对象
            required_permissions: 需要的权限列表

        Returns:
            用户信息字典，如果认证失败返回None
        """
        await self._get_handlers()

        # 1. 尝试从Authorization header获取JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除 "Bearer " 前缀
            return await self._authenticate_jwt(token, required_permissions)

        # 2. 尝试从X-API-Key header获取API Key
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return await self._authenticate_apikey(api_key, required_permissions)

        # 3. 没有认证信息
        logger.warning(f"Unauthorized request to {request.url.path}")
        return None

    async def _authenticate_jwt(
        self,
        token: str,
        required_permissions: Optional[List[Permission]] = None
    ) -> Optional[dict]:
        """JWT认证"""
        try:
            payload = self.jwt_handler.verify_access_token(token)
            if payload is None:
                logger.warning("Invalid JWT token")
                return None

            # 检查权限
            if required_permissions:
                user_role = payload.get("role", Role.GUEST)
                for perm in required_permissions:
                    if not has_permission(user_role, perm):
                        logger.warning(f"User {payload.get('sub')} lacks permission: {perm}")
                        return None

            return payload

        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            return None

    async def _authenticate_apikey(
        self,
        api_key: str,
        required_permissions: Optional[List[Permission]] = None
    ) -> Optional[dict]:
        """API Key认证"""
        try:
            # 验证API Key格式
            if not self.apikey_handler.validate_api_key_format(api_key):
                logger.warning("Invalid API key format")
                return None

            # 从缓存获取API Key信息（实际应用中应从数据库获取）
            cache_key = f"apikey:{api_key}"
            cached_user = await self.cache_manager.get(cache_key)

            if cached_user:
                user_info = eval(cached_user) if isinstance(cached_user, str) else cached_user

                # 检查权限
                if required_permissions:
                    user_role = user_info.get("role", Role.GUEST)
                    for perm in required_permissions:
                        if not has_permission(user_role, perm):
                            return None

                return user_info

            logger.warning(f"API key not found in cache: {api_key[:20]}...")
            return None

        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return None


# 全局认证中间件实例
_auth_middleware: Optional[AuthMiddleware] = None


def get_auth_middleware() -> AuthMiddleware:
    """获取全局认证中间件实例"""
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = AuthMiddleware()
    return _auth_middleware


async def require_auth(
    request: Request,
    required_permissions: Optional[List[Permission]] = None
) -> dict:
    """
    要求认证的依赖注入函数

    Args:
        request: FastAPI请求对象
        required_permissions: 需要的权限列表

    Returns:
        用户信息字典

    Raises:
        HTTPException: 如果认证失败
    """
    middleware = get_auth_middleware()
    user = await middleware.authenticate(request, required_permissions)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_permission(permission: Permission):
    """
    要求特定权限的依赖注入函数

    Args:
        permission: 需要的权限

    Returns:
        用户信息字典

    Raises:
        HTTPException: 如果权限不足
    """
    user = await require_auth(
        None,  # type: ignore
        [permission]
    )
    return user


# 角色权限检查函数
def require_role(role: Role):
    """要求特定角色的工厂函数"""
    async def _check_role(request: Request) -> dict:
        user = await require_auth(request, None)
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return user

    return _check_role


# 管理员权限检查
async def require_admin(request: Request) -> dict:
    """要求管理员权限"""
    return await require_role(Role.ADMIN)(request)


# 交易员权限检查
async def require_trader(request: Request) -> dict:
    """要求交易员权限"""
    return await require_role(Role.TRADER)(request)
