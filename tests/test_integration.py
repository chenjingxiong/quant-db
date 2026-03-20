# -*- coding: utf-8 -*-
"""
综合集成测试

测试各个模块之间的集成
"""
import pytest
import asyncio
from datetime import datetime, timedelta


@pytest.mark.asyncio
class TestAuthIntegration:
    """认证服务集成测试"""

    async def test_complete_auth_flow(self):
        """测试完整的认证流程"""
        from backend.services.auth import (
            get_auth_service,
            PasswordHandler,
            JWTHandler,
        )

        # 获取服务
        auth_service = await get_auth_service()
        password_handler = PasswordHandler()

        # 1. 密码加密
        password = "TestPassword123!"
        hashed_password = await auth_service.hash_password(password)

        # 2. 验证密码
        assert await auth_service.verify_password(password, hashed_password) is True
        assert await auth_service.verify_password("WrongPassword", hashed_password) is False

        # 3. 创建Token
        tokens = await auth_service.create_tokens(
            user_id=1,
            username="testuser",
            role="user",
        )

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

        # 4. 验证Token
        payload = await auth_service.verify_access_token(tokens["access_token"])
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"

        # 5. 刷新Token
        new_tokens = await auth_service.refresh_tokens(tokens["refresh_token"])
        assert new_tokens is not None
        assert new_tokens["access_token"] != tokens["access_token"]

    async def test_permission_check(self):
        """测试权限检查"""
        from backend.services.auth import Role, Permission, get_auth_service

        auth_service = await get_auth_service()

        # 管理员权限
        assert await auth_service.check_permission(
            Role.ADMIN, Permission.USER_MANAGE
        ) is True

        # 普通用户权限
        assert await auth_service.check_permission(
            Role.USER, Permission.STOCK_READ
        ) is True
        assert await auth_service.check_permission(
            Role.USER, Permission.USER_MANAGE
        ) is False


@pytest.mark.asyncio
class TestCacheIntegration:
    """缓存集成测试"""

    async def test_cache_with_auth(self):
        """测试缓存与认证结合"""
        from backend.cache import CacheManager
        from backend.services.auth import get_auth_service

        cache_manager = CacheManager()
        auth_service = await get_auth_service()

        # 创建Token并缓存
        tokens = await auth_service.create_tokens(
            user_id=1,
            username="testuser",
            role="user",
        )

        # 缓存用户会话
        session_data = {
            "user_id": 1,
            "username": "testuser",
            "role": "user",
            "token": tokens["access_token"],
        }

        assert await cache_manager.set(
            "session:1",
            session_data,
            ttl=3600,
            cache_type="user_session",
        )

        # 从缓存获取会话
        cached_session = await cache_manager.get("session:1")
        assert cached_session is not None
        assert cached_session["user_id"] == 1
        assert cached_session["username"] == "testuser"


@pytest.mark.asyncio
class TestMessagingIntegration:
    """消息队列集成测试"""

    async def test_publish_consume_flow(self):
        """测试发布-消费流程"""
        from backend.messaging import (
            get_rabbitmq_connection,
            MessagePublisher,
            MessageConsumer,
        )

        # 获取连接
        conn = await get_rabbitmq_connection()

        # 创建发布者和消费者
        publisher = MessagePublisher(conn)
        consumer = MessageConsumer("quote.processor", conn)

        # 注册回调
        received_messages = []

        async def callback(message):
            received_messages.append(message)

        consumer.register_callback("quote", callback)

        # 启动消费者
        await consumer.start()

        # 发布消息
        test_message = {
            "type": "quote",
            "symbol": "000001",
            "data": {"price": 10.5, "volume": 1000000},
        }

        assert await publisher.publish("quotes", "stock.sh.000001", test_message)

        # 等待消息处理
        await asyncio.sleep(1)

        # 验证消息
        assert len(received_messages) > 0

        # 清理
        await consumer.stop()


@pytest.mark.asyncio
class TestPostgresIntegration:
    """PostgreSQL集成测试"""

    async def test_database_operations(self):
        """测试数据库操作"""
        from backend.db import get_postgres_client

        # 获取客户端
        client = await get_postgres_client()

        # 健康检查
        assert await client.health_check() is True

        # 测试表是否存在
        assert await client.table_exists("users") is True

        # 查询测试
        result = await client.fetch_val("SELECT COUNT(*) FROM users")
        assert result is not None
        assert result >= 0  # 至少有默认的admin用户


@pytest.mark.asyncio
class TestEndToEndIntegration:
    """端到端集成测试"""

    async def test_user_login_flow(self):
        """测试用户登录流程"""
        from backend.services.auth import get_auth_service
        from backend.cache import CacheManager

        auth_service = await get_auth_service()
        cache_manager = CacheManager()

        username = "test_user"
        password = "TestPassword123!"

        # 1. 验证密码强度
        valid, errors = await auth_service.validate_password_strength(password)
        assert valid, f"Password validation failed: {errors}"

        # 2. 加密密码
        hashed = await auth_service.hash_password(password)

        # 3. 创建Token
        tokens = await auth_service.create_tokens(
            user_id=999,
            username=username,
            role="user",
        )

        # 4. 验证Token
        payload = await auth_service.verify_access_token(tokens["access_token"])
        assert payload is not None
        assert payload["username"] == username

        # 5. 创建会话
        assert await auth_service.create_session(
            user_id=999,
            access_token=tokens["access_token"],
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        # 6. 验证会话
        session = await auth_service.get_session(999)
        assert session is not None
        assert session["user_id"] == 999

        # 7. 记录审计日志
        from backend.services.auth import get_audit_logger

        audit_logger = await get_audit_logger()
        assert await audit_logger.log_auth(
            action="login",
            user_id=999,
            username=username,
            ip_address="127.0.0.1",
            success=True,
        )


# 性能测试
@pytest.mark.asyncio
class TestPerformance:
    """性能测试"""

    async def test_cache_performance(self):
        """测试缓存性能"""
        import time
        from backend.cache import CacheManager

        cache_manager = CacheManager()

        # 写入性能
        start = time.time()
        for i in range(1000):
            await cache_manager.set(f"perf_test_{i}", f"value_{i}")
        write_time = time.time() - start

        print(f"\n1000次缓存写入耗时: {write_time:.3f}秒")
        print(f"平均写入时间: {write_time/1000*1000:.2f}毫秒")

        # 读取性能
        start = time.time()
        for i in range(1000):
            await cache_manager.get(f"perf_test_{i}")
        read_time = time.time() - start

        print(f"1000次缓存读取耗时: {read_time:.3f}秒")
        print(f"平均读取时间: {read_time/1000*1000:.2f}毫秒")

        # 清理
        await cache_manager.clear_pattern("perf_test_*")

    async def test_jwt_performance(self):
        """测试JWT性能"""
        import time
        from backend.services.auth import JWTHandler

        handler = JWTHandler(secret_key="test_secret")

        # Token创建性能
        start = time.time()
        for i in range(1000):
            handler.create_access_token({"sub": str(i), "username": f"user_{i}"})
        create_time = time.time() - start

        print(f"\n1000次Token创建耗时: {create_time:.3f}秒")

        # Token验证性能
        token = handler.create_access_token({"sub": "1", "username": "test"})

        start = time.time()
        for i in range(1000):
            handler.verify_access_token(token)
        verify_time = time.time() - start

        print(f"1000次Token验证耗时: {verify_time:.3f}秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
