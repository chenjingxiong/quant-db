# -*- coding: utf-8 -*-
"""
API Key 处理模块

提供API Key的生成、验证和管理功能
"""
import secrets
import hashlib
from typing import Optional, Tuple
from loguru import logger


class APIKeyHandler:
    """API Key处理器"""

    # API Key前缀
    PREFIX = "qtk"

    def __init__(self):
        """初始化API Key处理器"""
        pass

    def generate_api_key(self) -> Tuple[str, str]:
        """
        生成新的API Key

        Returns:
            (api_key, key_hash)
        """
        # 生成32字节随机值
        random_bytes = secrets.token_bytes(32)

        # 构建API Key: qtk_<prefix>_<random>
        api_key = f"{self.PREFIX}_{secrets.token_urlsafe(16)}_{secrets.token_urlsafe(32)}"

        # 生成哈希值（用于安全存储）
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return api_key, key_hash

    def hash_api_key(self, api_key: str) -> str:
        """
        对API Key进行哈希

        Args:
            api_key: API Key

        Returns:
            哈希值
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str, key_hash: str) -> bool:
        """
        验证API Key

        Args:
            api_key: API Key
            key_hash: 存储的哈希值

        Returns:
            是否匹配
        """
        return self.hash_api_key(api_key) == key_hash

    def get_key_prefix(self, api_key: str) -> str:
        """
        获取API Key前缀（用于识别）

        Args:
            api_key: API Key

        Returns:
            密钥前缀
        """
        parts = api_key.split("_")
        if len(parts) >= 2:
            return parts[1]
        return ""

    def validate_api_key_format(self, api_key: str) -> bool:
        """
        验证API Key格式

        Args:
            api_key: API Key

        Returns:
            格式是否有效
        """
        parts = api_key.split("_")

        # 检查前缀
        if len(parts) < 3 or parts[0] != self.PREFIX:
            return False

        # 检查总长度（token_urlsafe 会产生约 4/3 的编码长度，加上前缀和分隔符）
        # 16 bytes -> ~22 chars, 32 bytes -> ~43 chars
        # 总长度应该在 qtk_ + 22 + _ + 43 = 71 左右
        if len(api_key) < 50:
            return False

        return True

    def extract_scope(self, scopes: list) -> set:
        """
        提取并规范化权限范围

        Args:
            scopes: 权限范围列表

        Returns:
            规范化后的权限范围集合
        """
        valid_scopes = {"read", "write", "admin"}
        return {s.lower() for s in scopes if s.lower() in valid_scopes}


# 全局实例
_apikey_handler: Optional[APIKeyHandler] = None


def get_apikey_handler() -> APIKeyHandler:
    """获取全局API Key处理器实例"""
    global _apikey_handler
    if _apikey_handler is None:
        _apikey_handler = APIKeyHandler()
    return _apikey_handler
