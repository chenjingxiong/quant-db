# -*- coding: utf-8 -*-
"""
缓存模块测试
"""
import pytest
import pytest_asyncio
import asyncio
from backend.cache import RedisClient, CacheManager, get_cache_manager


@pytest_asyncio.fixture
async def redis_client():
    """创建测试客户端"""
    client = RedisClient(host="localhost", port=6379, db=15)  # 使用测试数据库
    await client.connect()
    yield client
    await client.disconnect()


class TestRedisClient:
    """Redis客户端测试"""

    @pytest.mark.asyncio
    async def test_connect(self, redis_client):
        """测试连接"""
        assert redis_client.client is not None
        assert await redis_client.client.ping() is True

    @pytest.mark.asyncio
    async def test_set_get(self, redis_client):
        """测试设置和获取"""
        # 设置值
        assert await redis_client.set("test_key", "test_value")

        # 获取值
        value = await redis_client.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, redis_client):
        """测试带过期时间的设置"""
        # 设置2秒过期
        assert await redis_client.set("test_ttl", "value", ex=2)

        # 立即获取
        assert await redis_client.get("test_ttl") == "value"

        # 等待过期
        await asyncio.sleep(2.1)
        assert await redis_client.get("test_ttl") is None

    @pytest.mark.asyncio
    async def test_exists_delete(self, redis_client):
        """测试存在性和删除"""
        await redis_client.set("test_del", "value")

        assert await redis_client.exists("test_del") is True
        assert await redis_client.delete("test_del") is True
        assert await redis_client.exists("test_del") is False

    @pytest.mark.asyncio
    async def test_json_operations(self, redis_client):
        """测试JSON操作"""
        data = {"name": "test", "value": 123}

        # 设置JSON
        assert await redis_client.json_set("test_json", data)

        # 获取JSON
        result = await redis_client.json_get("test_json")
        assert result == data

    @pytest.mark.asyncio
    async def test_cache_operations(self, redis_client):
        """测试缓存操作"""
        data = {"symbol": "000001", "name": "平安银行"}

        # 缓存设置
        assert await redis_client.cache_set("test_cache", data, ttl=60)

        # 缓存获取
        result = await redis_client.cache_get("test_cache")
        assert result == data

    @pytest.mark.asyncio
    async def test_list_operations(self, redis_client):
        """测试列表操作"""
        # 清理可能存在的旧数据
        await redis_client.delete("test_list_ops")

        # 推入元素
        assert await redis_client.lpush("test_list_ops", "item1", "item2") == 2

        # 获取长度
        assert await redis_client.llen("test_list_ops") == 2

        # 弹出元素
        item = await redis_client.lpop("test_list_ops")
        assert item == "item2"

    @pytest.mark.asyncio
    async def test_set_operations(self, redis_client):
        """测试集合操作"""
        # 清理可能存在的旧数据
        await redis_client.delete("test_set_ops")

        # 添加成员
        assert await redis_client.sadd("test_set_ops", "member1", "member2") == 2

        # 检查成员
        assert await redis_client.sismember("test_set_ops", "member1") == 1

        # 获取所有成员
        members = await redis_client.smembers("test_set_ops")
        assert "member1" in members
        assert "member2" in members


class TestCacheManager:
    """缓存管理器测试"""

    @pytest_asyncio.fixture
    async def cache_manager(self, redis_client):
        """创建缓存管理器"""
        manager = CacheManager(redis_client=redis_client)
        yield manager

    @pytest.mark.asyncio
    async def test_get_set(self, cache_manager):
        """测试设置和获取"""
        # 设置值
        assert await cache_manager.set("test_key", "test_value")

        # 获取值
        value = await cache_manager.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_get_or_set(self, cache_manager):
        """测试获取或设置"""
        # 清理可能存在的旧数据
        await cache_manager.delete("test_or_set_unique")

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return "factory_value"

        # 第一次调用会执行工厂函数
        result1 = await cache_manager.get_or_set("test_or_set_unique", factory)
        assert result1 == "factory_value"
        assert call_count == 1

        # 第二次调用不会执行工厂函数（从缓存获取）
        result2 = await cache_manager.get_or_set("test_or_set_unique", factory)
        assert result2 == "factory_value"
        assert call_count == 1  # 没有增加

    @pytest.mark.asyncio
    async def test_cache_types(self, cache_manager):
        """测试不同缓存类型的TTL"""
        # 实时行情缓存（5秒）
        await cache_manager.set("quote_test_ttl", "value", cache_type="quotes")
        ttl = cache_manager.get_ttl("quotes")
        assert ttl == 5  # quotes类型默认5秒

    @pytest.mark.asyncio
    async def test_clear_pattern(self, cache_manager):
        """测试批量清除"""
        # 设置多个键
        await cache_manager.set("test:a", "value1")
        await cache_manager.set("test:b", "value2")
        await cache_manager.set("other:c", "value3")

        # 清除test:开头的键
        count = await cache_manager.clear_pattern("test:*")
        assert count >= 2

        # 验证清除结果
        assert await cache_manager.get("test:a") is None
        assert await cache_manager.get("test:b") is None
        assert await cache_manager.get("other:c") == "value3"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
