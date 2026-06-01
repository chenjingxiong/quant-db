# -*- coding: utf-8 -*-
"""
数据库连接池优化

提供高效的数据库连接管理和查询优化
"""
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from loguru import logger
import asyncpg
from asyncpg.pool import Pool


class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(
        self,
        dsn: str,
        min_size: int = 5,
        max_size: int = 20,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0,
    ):
        """
        初始化连接池管理器

        Args:
            dsn: 数据库连接字符串
            min_size: 最小连接数
            max_size: 最大连接数
            max_queries: 单个连接最大查询数
            max_inactive_connection_lifetime: 非活跃连接最大生存时间（秒）
        """
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime

        self._pool: Optional[Pool] = None

    async def initialize(self):
        """初始化连接池"""
        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=self.min_size,
            max_size=self.max_size,
            max_queries=self.max_queries,
            max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
            command_timeout=60,
        )
        logger.info(f"数据库连接池已创建: min={self.min_size}, max={self.max_size}")

    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("数据库连接池已关闭")

    @asynccontextmanager
    async def acquire(self):
        """
        获取连接上下文管理器

        使用示例:
            async with pool_manager.acquire() as conn:
                result = await conn.fetch("SELECT * FROM users")
        """
        if not self._pool:
            raise RuntimeError("连接池未初始化")

        async with self._pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args, timeout: float = 30.0) -> str:
        """
        执行SQL语句（无结果）

        Args:
            query: SQL语句
            *args: 查询参数
            timeout: 超时时间

        Returns:
            执行状态
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def fetch(
        self,
        query: str,
        *args,
        timeout: float = 30.0
    ) -> List[asyncpg.Record]:
        """
        执行查询并返回所有结果

        Args:
            query: SQL语句
            *args: 查询参数
            timeout: 超时时间

        Returns:
            查询结果列表
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetchone(
        self,
        query: str,
        *args,
        timeout: float = 30.0
    ) -> Optional[asyncpg.Record]:
        """
        执行查询并返回单行结果

        Args:
            query: SQL语句
            *args: 查询参数
            timeout: 超时时间

        Returns:
            查询结果行，None表示无结果
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def fetchval(
        self,
        query: str,
        *args,
        column: int = 0,
        timeout: float = 30.0
    ) -> Any:
        """
        执行查询并返回单个值

        Args:
            query: SQL语句
            *args: 查询参数
            column: 列索引
            timeout: 超时时间

        Returns:
            查询结果值
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, column=column, timeout=timeout)

    async def executemany(
        self,
        command: str,
        args_list: List[tuple],
        timeout: float = 30.0
    ) -> None:
        """
        批量执行SQL语句

        Args:
            command: SQL语句
            args_list: 参数列表
            timeout: 超时时间
        """
        async with self.acquire() as conn:
            await conn.executemany(command, args_list, timeout=timeout)

    async def transaction(self):
        """
        事务上下文管理器

        使用示例:
            async with pool_manager.transaction():
                await pool.execute("INSERT INTO users ...")
                await pool.execute("UPDATE users ...")
        """
        if not self._pool:
            raise RuntimeError("连接池未初始化")

        return self._pool.transaction()

    def get_pool_info(self) -> Dict[str, Any]:
        """获取连接池信息"""
        if not self._pool:
            return {"status": "not_initialized"}

        return {
            "status": "initialized",
            "min_size": self._pool._minsize,
            "max_size": self._pool._maxsize,
            "size": self._pool._size,
            "available": self._pool._queue.qsize(),
        }


class QueryOptimizer:
    """查询优化器"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化查询优化器

        Args:
            pool_manager: 连接池管理器
        """
        self.pool_manager = pool_manager
        self._query_cache: Dict[str, Any] = {}

    async def fetch_paginated(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        *args,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        分页查询优化

        Args:
            query: SQL查询语句
            page: 页码（从1开始）
            page_size: 每页数量
            *args: 查询参数
            timeout: 超时时间

        Returns:
            分页结果
        """
        offset = (page - 1) * page_size

        # 使用游标进行高效分页
        paginated_query = f"""
            SELECT * FROM ({query}) AS subquery
            LIMIT {page_size} OFFSET {offset}
        """

        # 同时获取总数（在同一个事务中）
        count_query = f"SELECT COUNT(*) FROM ({query}) AS subquery"

        async with self.pool_manager.acquire() as conn:
            async with conn.transaction():
                # 获取总数
                total = await conn.fetchval(count_query, *args)

                # 获取当前页数据
                rows = await conn.fetch(paginated_query, *args, timeout=timeout)

        return {
            "data": [dict(row) for row in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }
        }

    async def fetch_with_cache(
        self,
        query: str,
        cache_key: str,
        cache_ttl: int = 300,
        *args,
        timeout: float = 30.0
    ) -> List[Dict]:
        """
        带缓存的查询

        Args:
            query: SQL查询语句
            cache_key: 缓存键
            cache_ttl: 缓存时间（秒）
            *args: 查询参数
            timeout: 超时时间

        Returns:
            查询结果
        """
        # 尝试从缓存获取
        if cache_key in self._query_cache:
            logger.debug(f"查询缓存命中: {cache_key}")
            return self._query_cache[cache_key]

        # 执行查询
        rows = await self.pool_manager.fetch(query, *args, timeout=timeout)
        result = [dict(row) for row in rows]

        # 存入缓存
        self._query_cache[cache_key] = result

        # 设置缓存过期
        async def expire_cache():
            await asyncio.sleep(cache_ttl)
            if cache_key in self._query_cache:
                del self._query_cache[cache_key]

        asyncio.create_task(expire_cache())

        return result

    def invalidate_cache(self, pattern: Optional[str] = None):
        """
        使缓存失效

        Args:
            pattern: 缓存键模式，None表示清空所有
        """
        if pattern is None:
            self._query_cache.clear()
            logger.info("已清空所有查询缓存")
        else:
            keys_to_delete = [k for k in self._query_cache if pattern in k]
            for key in keys_to_delete:
                del self._query_cache[key]
            logger.info(f"已清除 {len(keys_to_delete)} 个匹配的缓存")

    async def batch_insert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        批量插入优化

        Args:
            table: 表名
            data: 数据列表
            batch_size: 批次大小

        Returns:
            插入的行数
        """
        if not data:
            return 0

        # 获取列名
        columns = list(data[0].keys())
        col_names = ', '.join(columns)
        placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))

        query = f"""
            INSERT INTO {table} ({col_names})
            VALUES ({placeholders})
        """

        total_inserted = 0
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            args_list = [
                tuple(row.get(col) for col in columns)
                for row in batch
            ]

            await self.pool_manager.executemany(query, args_list)
            total_inserted += len(batch)

            logger.debug(f"批量插入: {len(batch)} 行到 {table}")

        return total_inserted
