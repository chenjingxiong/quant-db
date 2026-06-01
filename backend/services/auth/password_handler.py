# -*- coding: utf-8 -*-
"""
密码处理模块

提供密码加密、验证等功能
"""
import hashlib
import hmac
from typing import Optional
from loguru import logger


class PasswordHandler:
    """密码处理器"""

    def __init__(self):
        """初始化密码处理器"""
        # 使用SHA-256 + salt的方式（兼容性更好）
        pass

    def _generate_salt(self) -> str:
        """生成随机盐值"""
        import secrets
        return secrets.token_hex(16)

    def hash_password(self, password: str) -> str:
        """
        加密密码

        Args:
            password: 明文密码

        Returns:
            加密后的密码（格式：salt$hash）
        """
        try:
            salt = self._generate_salt()
            # 使用PBKDF2进行哈希
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000,  # 迭代次数
            )
            password_hash = hash_obj.hex()

            # 返回格式：salt$hash
            return f"{salt}${password_hash}"
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证密码

        Args:
            plain_password: 明文密码
            hashed_password: 加密密码

        Returns:
            是否匹配
        """
        try:
            if "$" not in hashed_password:
                return False

            salt, stored_hash = hashed_password.split("$", 1)

            # 使用相同的盐值计算哈希
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                plain_password.encode('utf-8'),
                salt.encode('utf-8'),
                100000,
            )
            computed_hash = hash_obj.hex()

            # 使用恒定时间比较防止时序攻击
            return hmac.compare_digest(computed_hash.encode(), stored_hash.encode())
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        检查密码是否需要重新加密

        Args:
            hashed_password: 加密密码

        Returns:
            是否需要重新加密
        """
        # PBKDF2不需要重新哈希
        return False

    def validate_strength(self, password: str) -> tuple[bool, list[str]]:
        """
        验证密码强度

        Args:
            password: 密码

        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []

        # 长度检查
        if len(password) < 8:
            errors.append("密码长度至少8位")

        if len(password) > 128:
            errors.append("密码长度不能超过128位")

        # 复杂度检查
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?`~" for c in password)

        complexity_count = sum([has_lower, has_upper, has_digit, has_special])

        if complexity_count < 3:
            errors.append("密码必须包含大写字母、小写字母、数字和特殊字符中的至少3种")

        # 常见弱密码检查
        weak_passwords = [
            "password",
            "12345678",
            "abcdefgh",
            "qwerty123",
            "abc12345",
        ]
        if password.lower() in weak_passwords:
            errors.append("密码过于简单，请使用更复杂的密码")

        return len(errors) == 0, errors


# 全局实例
_password_handler: Optional[PasswordHandler] = None


def get_password_handler() -> PasswordHandler:
    """获取全局密码处理器实例"""
    global _password_handler
    if _password_handler is None:
        _password_handler = PasswordHandler()
    return _password_handler
