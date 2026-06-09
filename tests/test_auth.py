# -*- coding: utf-8 -*-
"""
认证服务模块测试
"""
import pytest
from backend.services.auth import (
    PasswordHandler,
    JWTHandler,
    APIKeyHandler,
    Permission,
    Role,
    has_permission,
)


class TestPasswordHandler:
    """密码处理器测试"""

    @pytest.fixture
    def handler(self):
        return PasswordHandler()

    def test_hash_password(self, handler):
        """测试密码加密"""
        password = "TestPass123!"  # bcrypt限制72字节
        hashed = handler.hash_password(password)

        assert hashed != password
        assert len(hashed) > 20

    def test_verify_password(self, handler):
        """测试密码验证"""
        password = "TestPass123!"
        hashed = handler.hash_password(password)

        assert handler.verify_password(password, hashed) is True
        assert handler.verify_password("WrongPass!", hashed) is False

    def test_validate_strength(self, handler):
        """测试密码强度验证"""
        # 强密码
        valid, errors = handler.validate_strength("StrongPass123!@#")
        assert valid is True
        assert len(errors) == 0

        # 弱密码
        valid, errors = handler.validate_strength("weak")
        assert valid is False
        assert len(errors) > 0


class TestJWTHandler:
    """JWT处理器测试"""

    @pytest.fixture
    def handler(self):
        return JWTHandler(
            secret_key="test_secret_key_for_testing_only",
            algorithm="HS256",
            access_token_expire_minutes=30,
        )

    def test_create_access_token(self, handler):
        """测试创建访问令牌"""
        data = {"sub": "123", "username": "testuser", "role": "user"}
        token = handler.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_verify_access_token(self, handler):
        """测试验证访问令牌"""
        data = {"sub": "123", "username": "testuser", "role": "user"}
        token = handler.create_access_token(data)

        payload = handler.verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"

    def test_invalid_token(self, handler):
        """测试无效令牌"""
        payload = handler.verify_access_token("invalid_token")
        assert payload is None

    def test_refresh_token(self, handler):
        """测试刷新令牌"""
        data = {"sub": "123", "username": "testuser", "role": "user"}

        access_token = handler.create_access_token(data)
        refresh_token = handler.create_refresh_token(data)

        # 访问令牌验证
        access_payload = handler.verify_access_token(access_token)
        assert access_payload is not None
        assert access_payload.get("type") == "access"

        # 刷新令牌验证
        refresh_payload = handler.verify_refresh_token(refresh_token)
        assert refresh_payload is not None
        assert refresh_payload.get("type") == "refresh"


class TestAPIKeyHandler:
    """API Key处理器测试"""

    @pytest.fixture
    def handler(self):
        return APIKeyHandler()

    def test_generate_api_key(self, handler):
        """测试生成API Key"""
        api_key, key_hash = handler.generate_api_key()

        assert api_key.startswith("qtk_")
        assert len(api_key) > 50
        assert len(key_hash) == 64  # SHA256 hex length

    def test_hash_api_key(self, handler):
        """测试API Key哈希"""
        api_key = "qtk_test_key"
        hash1 = handler.hash_api_key(api_key)
        hash2 = handler.hash_api_key(api_key)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_verify_api_key(self, handler):
        """测试验证API Key"""
        api_key, key_hash = handler.generate_api_key()

        assert handler.verify_api_key(api_key, key_hash) is True
        assert handler.verify_api_key("wrong_key", key_hash) is False

    def test_validate_format(self, handler):
        """测试格式验证"""
        # 有效格式
        valid_key, _ = handler.generate_api_key()
        assert handler.validate_api_key_format(valid_key) is True

        # 无效格式
        assert handler.validate_api_key_format("invalid") is False
        assert handler.validate_api_key_format("qtk_short") is False

    def test_get_key_prefix(self, handler):
        """测试获取密钥前缀"""
        api_key = "qtk_prefix_random_randompart"
        prefix = handler.get_key_prefix(api_key)

        assert prefix == "prefix"


class TestPermissions:
    """权限测试"""

    def test_role_has_permission(self):
        """测试角色权限"""
        # 管理员拥有所有权限
        assert has_permission(Role.ADMIN, Permission.USER_MANAGE) is True
        assert has_permission(Role.ADMIN, Permission.STOCK_READ) is True

        # 普通用户只有读权限
        assert has_permission(Role.USER, Permission.STOCK_READ) is True
        assert has_permission(Role.USER, Permission.USER_MANAGE) is False

        # 访客只有基础读权限
        assert has_permission(Role.GUEST, Permission.STOCK_READ) is True
        assert has_permission(Role.GUEST, Permission.COLLECT_START) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
