# -*- coding: utf-8 -*-
"""
Redis客户端封装

提供统一的Redis访问接口，支持连接池、自动重连等
"""
import asyncio
import json
import pickle
from typing import Any, Optional, List, Dict
from loguru import logger
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError


class RedisClient:
    """Redis客户端封装类"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        encoding: str = "utf-8",
        decode_responses: bool = True,
        max_connections: int = 50,
    ):
        """
        初始化Redis客户端

        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库编号
            password: 密码
            encoding: 编码
            decode_responses: 是否自动解码响应
            max_connections: 最大连接数
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.encoding = encoding
        self.decode_responses = decode_responses
        self.max_connections = max_connections

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self) -> bool:
        """
        连接到Redis服务器

        Returns:
            是否连接成功
        """
        try:
            self._pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                encoding=self.encoding,
                decode_responses=self.decode_responses,
                max_connections=self.max_connections,
            )
            self._client = Redis(connection_pool=self._pool)

            # 测试连接
            await self._client.ping()
            logger.info(
                f"Connected to Redis: {self.host}:{self.port}, db={self.db}"
            )
            return True

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    async def disconnect(self) -> None:
        """断开Redis连接"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Disconnected from Redis")

    @property
    def client(self) -> Redis:
        """获取Redis客户端"""
        if self._client is None:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self._client

    # ===========================
    # 字符串操作
    # ===========================

    async def get(self, key: str) -> Optional[str]:
        """获取字符串值"""
        try:
            return await self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(
        self, key: str, value: str, ex: Optional[int] = None, px: Optional[int] = None
    ) -> bool:
        """
        设置字符串值

        Args:
            key: 键
            value: 值
            ex: 过期时间（秒）
            px: 过期时间（毫秒）

        Returns:
            是否设置成功
        """
        try:
            await self.client.set(key, value, ex=ex, px=px)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除键"""
        try:
            await self.client.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return await self.client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        try:
            return await self.client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL error: {e}")
            return -1

    # ===========================
    # JSON操作
    # ===========================

    async def json_get(self, key: str) -> Optional[Dict]:
        """获取JSON值"""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis JSON GET error: {e}")
            return None

    async def json_set(
        self, key: str, value: Dict, ex: Optional[int] = None
    ) -> bool:
        """设置JSON值"""
        try:
            json_str = json.dumps(value)
            await self.client.set(key, json_str, ex=ex)
            return True
        except (RedisError, TypeError) as e:
            logger.error(f"Redis JSON SET error: {e}")
            return False

    # ===========================
    # Hash操作
    # ===========================

    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段值"""
        try:
            return await self.client.hget(name, key)
        except RedisError as e:
            logger.error(f"Redis HGET error: {e}")
            return None

    async def hset(self, name: str, key: str, value: str) -> bool:
        """设置哈希字段值"""
        try:
            await self.client.hset(name, key, value)
            return True
        except RedisError as e:
            logger.error(f"Redis HSET error: {e}")
            return False

    async def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有哈希字段"""
        try:
            return await self.client.hgetall(name)
        except RedisError as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> bool:
        """删除哈希字段"""
        try:
            await self.client.hdel(name, *keys)
            return True
        except RedisError as e:
            logger.error(f"Redis HDEL error: {e}")
            return False

    # ===========================
    # 列表操作
    # ===========================

    async def lpush(self, name: str, *values: str) -> int:
        """从左侧推入列表"""
        try:
            return await self.client.lpush(name, *values)
        except RedisError as e:
            logger.error(f"Redis LPUSH error: {e}")
            return 0

    async def rpush(self, name: str, *values: str) -> int:
        """从右侧推入列表"""
        try:
            return await self.client.rpush(name, *values)
        except RedisError as e:
            logger.error(f"Redis RPUSH error: {e}")
            return 0

    async def lpop(self, name: str) -> Optional[str]:
        """从左侧弹出列表"""
        try:
            return await self.client.lpop(name)
        except RedisError as e:
            logger.error(f"Redis LPOP error: {e}")
            return None

    async def lrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        """获取列表范围"""
        try:
            return await self.client.lrange(name, start, end)
        except RedisError as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []

    async def llen(self, name: str) -> int:
        """获取列表长度"""
        try:
            return await self.client.llen(name)
        except RedisError as e:
            logger.error(f"Redis LLEN error: {e}")
            return 0

    # ===========================
    # 集合操作
    # ===========================

    async def sadd(self, name: str, *values: str) -> int:
        """添加到集合"""
        try:
            return await self.client.sadd(name, *values)
        except RedisError as e:
            logger.error(f"Redis SADD error: {e}")
            return 0

    async def srem(self, name: str, *values: str) -> int:
        """从集合移除"""
        try:
            return await self.client.srem(name, *values)
        except RedisError as e:
            logger.error(f"Redis SREM error: {e}")
            return 0

    async def smembers(self, name: str) -> set:
        """获取集合所有成员"""
        try:
            return await self.client.smembers(name)
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()

    async def sismember(self, name: str, value: str) -> bool:
        """检查是否是集合成员"""
        try:
            return await self.client.sismember(name, value)
        except RedisError as e:
            logger.error(f"Redis SISMEMBER error: {e}")
            return False

    # ===========================
    # 有序集合操作
    # ===========================

    async def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """添加到有序集合"""
        try:
            return await self.client.zadd(name, mapping)
        except RedisError as e:
            logger.error(f"Redis ZADD error: {e}")
            return 0

    async def zrem(self, name: str, *values: str) -> int:
        """从有序集合移除"""
        try:
            return await self.client.zrem(name, *values)
        except RedisError as e:
            logger.error(f"Redis ZREM error: {e}")
            return 0

    async def zrange(
        self, name: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> List:
        """获取有序集合范围"""
        try:
            return await self.client.zrange(name, start, end, withscores=withscores)
        except RedisError as e:
            logger.error(f"Redis ZRANGE error: {e}")
            return []

    async def zrevrange(
        self, name: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> List:
        """获取有序集合范围（降序）"""
        try:
            return await self.client.zrevrange(name, start, end, withscores=withscores)
        except RedisError as e:
            logger.error(f"Redis ZREVRANGE error: {e}")
            return []

    # ===========================
    # 分布式锁
    # ===========================

    async def acquire_lock(
        self, lock_name: str, acquire_timeout: int = 10, lock_timeout: int = 30
    ) -> Optional[str]:
        """
        获取分布式锁

        Args:
            lock_name: 锁名称
            acquire_timeout: 获取锁超时时间（秒）
            lock_timeout: 锁超时时间（秒）

        Returns:
            锁标识符，如果获取失败返回None
        """
        import time
        import uuid

        lock_value = str(uuid.uuid4())
        end_time = time.time() + acquire_timeout

        while time.time() < end_time:
            try:
                # 使用SET命令的NX选项实现锁
                acquired = await self.client.set(
                    f"lock:{lock_name}",
                    lock_value,
                    nx=True,
                    ex=lock_timeout,
                )
                if acquired:
                    logger.debug(f"Acquired lock: {lock_name}")
                    return lock_value
            except RedisError as e:
                logger.error(f"Redis lock acquire error: {e}")

            await asyncio.sleep(0.01)

        logger.warning(f"Failed to acquire lock: {lock_name}")
        return None

    async def release_lock(self, lock_name: str, lock_value: str) -> bool:
        """
        释放分布式锁

        Args:
            lock_name: 锁名称
            lock_value: 锁标识符

        Returns:
            是否释放成功
        """
        try:
            # 使用Lua脚本确保只释放自己持有的锁
            lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
            """
            result = await self.client.eval(
                lua_script, 1, f"lock:{lock_name}", lock_value
            )
            if result:
                logger.debug(f"Released lock: {lock_name}")
                return True
            return False
        except RedisError as e:
            logger.error(f"Redis lock release error: {e}")
            return False

    # ===========================
    # 缓存管理
    # ===========================

    async def cache_get(
        self, key: str, default: Optional[Any] = None
    ) -> Optional[Any]:
        """
        获取缓存数据

        支持自动序列化/反序列化
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return default

            # 尝试JSON反序列化
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except RedisError as e:
            logger.error(f"Redis cache GET error: {e}")
            return default

    async def cache_set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存数据

        支持自动序列化
        """
        try:
            # 尝试JSON序列化
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = str(value)
            else:
                # 使用pickle序列化复杂对象
                serialized_value = pickle.dumps(value)

            await self.client.set(key, serialized_value, ex=ttl)
            return True
        except RedisError as e:
            logger.error(f"Redis cache SET error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        批量删除匹配模式的键

        Args:
            pattern: 键模式（如 "user:*"）

        Returns:
            删除的键数量
        """
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0


# ===========================
# 全局客户端实例
# ===========================

_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """
    获取全局Redis客户端实例

    Returns:
        Redis客户端实例
    """
    global _redis_client

    if _redis_client is None:
        from ..config import get_settings

        settings = get_settings()
        _redis_client = RedisClient(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
        await _redis_client.connect()

    return _redis_client
