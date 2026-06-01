# -*- coding: utf-8 -*-
"""
JWT Token 处理模块

提供JWT Token的生成、验证、刷新等功能
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from loguru import logger


class JWTHandler:
    """JWT Token处理器"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        初始化JWT处理器

        Args:
            secret_key: 密钥
            algorithm: 加密算法
            access_token_expire_minutes: 访问令牌过期时间（分钟）
            refresh_token_expire_days: 刷新令牌过期时间（天）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建访问令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT Token
        """
        to_encode = data.copy()

        # 设置过期时间
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        })

        try:
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建刷新令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            刷新令牌
        """
        to_encode = data.copy()

        # 设置过期时间
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32),  # 唯一ID
        })

        try:
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        解码令牌

        Args:
            token: JWT Token

        Returns:
            解码后的数据，如果解码失败返回None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error decoding token: {e}")
            return None

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证访问令牌

        Args:
            token: JWT Token

        Returns:
            令牌数据，如果验证失败返回None
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        # 检查令牌类型
        if payload.get("type") != "access":
            logger.warning("Invalid token type: expected 'access'")
            return None

        return payload

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证刷新令牌

        Args:
            token: 刷新令牌

        Returns:
            令牌数据，如果验证失败返回None
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        # 检查令牌类型
        if payload.get("type") != "refresh":
            logger.warning("Invalid token type: expected 'refresh'")
            return None

        return payload

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        获取令牌过期时间

        Args:
            token: JWT Token

        Returns:
            过期时间，如果解析失败返回None
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None

    def is_token_expired(self, token: str) -> bool:
        """
        检查令牌是否已过期

        Args:
            token: JWT Token

        Returns:
            是否已过期
        """
        expiry = self.get_token_expiry(token)
        if expiry is None:
            return True
        return datetime.now(timezone.utc) > expiry


# 全局实例
_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """获取全局JWT处理器实例"""
    global _jwt_handler
    if _jwt_handler is None:
        from ...config import get_settings

        settings = get_settings()
        _jwt_handler = JWTHandler(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        )
    return _jwt_handler
