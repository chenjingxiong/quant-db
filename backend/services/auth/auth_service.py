# -*- coding: utf-8 -*-
"""
认证服务模块

提供用户认证、授权、Token管理等功能
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger

from .jwt_handler import JWTHandler, get_jwt_handler
from .password_handler import PasswordHandler, get_password_handler
from .permissions import Role, Permission, has_permission
from ...cache import CacheManager, get_cache_manager


class AuthService:
    """认证服务"""

    def __init__(
        self,
        jwt_handler: Optional[JWTHandler] = None,
        password_handler: Optional[PasswordHandler] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        """
        初始化认证服务

        Args:
            jwt_handler: JWT处理器
            password_handler: 密码处理器
            cache_manager: 缓存管理器
        """
        self.jwt_handler = jwt_handler
        self.password_handler = password_handler
        self.cache_manager = cache_manager

    async def _get_jwt_handler(self) -> JWTHandler:
        """获取JWT处理器"""
        if self.jwt_handler is None:
            return get_jwt_handler()
        return self.jwt_handler

    async def _get_password_handler(self) -> PasswordHandler:
        """获取密码处理器"""
        if self.password_handler is None:
            return get_password_handler()
        return self.password_handler

    async def _get_cache_manager(self) -> CacheManager:
        """获取缓存管理器"""
        if self.cache_manager is None:
            return get_cache_manager()
        return self.cache_manager

    # ===========================
    # 密码验证
    # ===========================

    async def verify_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """
        验证密码

        Args:
            plain_password: 明文密码
            hashed_password: 加密密码

        Returns:
            是否匹配
        """
        handler = await self._get_password_handler()
        return handler.verify_password(plain_password, hashed_password)

    async def hash_password(self, plain_password: str) -> str:
        """
        加密密码

        Args:
            plain_password: 明文密码

        Returns:
            加密后的密码
        """
        handler = await self._get_password_handler()
        return handler.hash_password(plain_password)

    async def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """
        验证密码强度

        Args:
            password: 密码

        Returns:
            (是否通过, 错误信息列表)
        """
        handler = await self._get_password_handler()
        return handler.validate_strength(password)

    # ===========================
    # Token管理
    # ===========================

    async def create_tokens(
        self, user_id: int, username: str, role: Role, extra_claims: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建访问令牌和刷新令牌

        Args:
            user_id: 用户ID
            username: 用户名
            role: 角色
            extra_claims: 额外的声明

        Returns:
            包含access_token和refresh_token的字典
        """
        jwt_handler = await self._get_jwt_handler()

        # 构建令牌数据
        base_claims = {
            "sub": str(user_id),
            "username": username,
            "role": role.value,
        }

        if extra_claims:
            base_claims.update(extra_claims)

        # 创建访问令牌
        access_token = jwt_handler.create_access_token(base_claims)

        # 创建刷新令牌
        refresh_token = jwt_handler.create_refresh_token(base_claims)

        # 缓存刷新令牌
        cache_manager = await self._get_cache_manager()
        await cache_manager.set(
            f"refresh_token:{user_id}",
            refresh_token,
            ttl=7 * 24 * 3600,  # 7天
            cache_type="user_session",
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_handler.access_token_expire_minutes * 60,
        }

    async def refresh_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的令牌对，如果刷新失败返回None
        """
        jwt_handler = await self._get_jwt_handler()
        cache_manager = await self._get_cache_manager()

        # 验证刷新令牌
        payload = jwt_handler.verify_refresh_token(refresh_token)
        if payload is None:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # 检查缓存的刷新令牌是否匹配
        cached_token = await cache_manager.get(f"refresh_token:{user_id}")
        if cached_token != refresh_token:
            logger.warning(f"Invalid refresh token for user {user_id}")
            return None

        # 创建新的令牌对
        return await self.create_tokens(
            user_id=int(user_id),
            username=payload.get("username", ""),
            role=Role(payload.get("role", "user")),
        )

    async def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证访问令牌

        Args:
            token: 访问令牌

        Returns:
            令牌数据，如果验证失败返回None
        """
        jwt_handler = await self._get_jwt_handler()
        return jwt_handler.verify_access_token(token)

    async def revoke_tokens(self, user_id: int) -> bool:
        """
        撤销用户的所有令牌

        Args:
            user_id: 用户ID

        Returns:
            是否撤销成功
        """
        cache_manager = await self._get_cache_manager()
        return await cache_manager.delete(f"refresh_token:{user_id}")

    # ===========================
    # 权限检查
    # ===========================

    async def check_permission(
        self, user_role: Role, required_permission: Permission
    ) -> bool:
        """
        检查用户是否拥有指定权限

        Args:
            user_role: 用户角色
            required_permission: 需要的权限

        Returns:
            是否拥有权限
        """
        return has_permission(user_role, required_permission)

    async def require_permission(
        self, user_role: Role, required_permission: Permission
    ) -> None:
        """
        要求用户拥有指定权限，否则抛出异常

        Args:
            user_role: 用户角色
            required_permission: 需要的权限

        Raises:
            PermissionError: 如果用户没有所需权限
        """
        if not await self.check_permission(user_role, required_permission):
            raise PermissionError(
                f"User with role '{user_role.value}' does not have "
                f"required permission '{required_permission.value}'"
            )

    # ===========================
    # 会话管理
    # ===========================

    async def create_session(
        self,
        user_id: int,
        access_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        创建用户会话

        Args:
            user_id: 用户ID
            access_token: 访问令牌
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            是否创建成功
        """
        cache_manager = await self._get_cache_manager()

        session_data = {
            "user_id": user_id,
            "access_token": access_token,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
        }

        return await cache_manager.set(
            f"session:{user_id}",
            session_data,
            ttl=24 * 3600,  # 24小时
            cache_type="user_session",
        )

    async def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户会话

        Args:
            user_id: 用户ID

        Returns:
            会话数据，如果不存在返回None
        """
        cache_manager = await self._get_cache_manager()
        return await cache_manager.get(f"session:{user_id}")

    async def delete_session(self, user_id: int) -> bool:
        """
        删除用户会话

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        cache_manager = await self._get_cache_manager()
        return await cache_manager.delete(f"session:{user_id}")


# 全局实例
_auth_service: Optional[AuthService] = None


async def get_auth_service() -> AuthService:
    """获取全局认证服务实例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
