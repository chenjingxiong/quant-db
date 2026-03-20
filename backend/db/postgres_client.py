# -*- coding: utf-8 -*-
"""
PostgreSQL客户端封装

提供PostgreSQL数据库连接和操作接口
"""
import asyncpg
from typing import Any, Optional, List, Dict, Tuple
from loguru import logger


class PostgresClient:
    """PostgreSQL客户端封装类"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "postgres",
        password: str = "",
        database: str = "postgres",
        min_size: int = 10,
        max_size: int = 50,
        command_timeout: int = 60,
    ):
        """
        初始化PostgreSQL客户端

        Args:
            host: 主机地址
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
            min_size: 最小连接数
            max_size: 最大连接数
            command_timeout: 命令超时时间（秒）
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.command_timeout = command_timeout

        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> bool:
        """
        创建连接池

        Returns:
            是否连接成功
        """
        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.command_timeout,
            )

            # 测试连接
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            logger.info(
                f"Connected to PostgreSQL: {self.host}:{self.port}, db={self.database}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    async def disconnect(self) -> None:
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
            logger.info("Disconnected from PostgreSQL")

    @property
    def pool(self) -> asyncpg.Pool:
        """获取连接池"""
        if self._pool is None:
            raise RuntimeError("PostgreSQL pool is not initialized. Call connect() first.")
        return self._pool

    # ===========================
    # 查询操作
    # ===========================

    async def fetch_one(
        self, query: str, *args, timeout: Optional[float] = None
    ) -> Optional[asyncpg.Record]:
        """
        查询单条记录

        Args:
            query: SQL查询语句
            *args: 查询参数
            timeout: 超时时间

        Returns:
            记录对象，如果不存在返回None
        """
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetchrow(query, *args, timeout=timeout)
        except Exception as e:
            logger.error(f"Error in fetch_one: {e}, query: {query}")
            return None

    async def fetch_all(
        self, query: str, *args, timeout: Optional[float] = None
    ) -> List[asyncpg.Record]:
        """
        查询所有记录

        Args:
            query: SQL查询语句
            *args: 查询参数
            timeout: 超时时间

        Returns:
            记录列表
        """
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetch(query, *args, timeout=timeout)
        except Exception as e:
            logger.error(f"Error in fetch_all: {e}, query: {query}")
            return []

    async def fetch_val(
        self, query: str, *args, column: Any = 0, timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        查询单个值

        Args:
            query: SQL查询语句
            *args: 查询参数
            column: 列索引或名称
            timeout: 超时时间

        Returns:
            查询结果值
        """
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetchval(query, *args, column=column, timeout=timeout)
        except Exception as e:
            logger.error(f"Error in fetch_val: {e}, query: {query}")
            return None

    # ===========================
    # 执行操作
    # ===========================

    async def execute(
        self, query: str, *args, timeout: Optional[float] = None
    ) -> str:
        """
        执行SQL语句

        Args:
            query: SQL语句
            *args: 参数
            timeout: 超时时间

        Returns:
            执行结果状态
        """
        try:
            async with self._pool.acquire() as conn:
                return await conn.execute(query, *args, timeout=timeout)
        except Exception as e:
            logger.error(f"Error in execute: {e}, query: {query}")
            raise

    async def executemany(
        self, query: str, args: List[Tuple], timeout: Optional[float] = None
    ) -> str:
        """
        批量执行SQL语句

        Args:
            query: SQL语句
            args: 参数列表
            timeout: 超时时间

        Returns:
            执行结果状态
        """
        try:
            async with self._pool.acquire() as conn:
                return await conn.executemany(query, args, timeout=timeout)
        except Exception as e:
            logger.error(f"Error in executemany: {e}, query: {query}")
            raise

    # ===========================
    # 事务操作
    # ===========================

    async def transaction(self):
        """
        获取事务对象

        Usage:
            async with client.transaction() as trans:
                await trans.execute("INSERT INTO ...")
                await trans.execute("UPDATE ...")
        """
        return self._pool.transaction()

    # ===========================
    # 常用快捷操作
    # ===========================

    async def insert(
        self,
        table: str,
        data: Dict[str, Any],
        returning: Optional[str] = None,
    ) -> Optional[Any]:
        """
        插入记录

        Args:
            table: 表名
            data: 数据字典
            returning: 返回字段

        Returns:
            返回值（如果指定了returning）
        """
        columns = data.keys()
        values = data.values()
        placeholders = [f"${i + 1}" for i in range(len(data))]

        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        if returning:
            query += f" RETURNING {returning}"

        return await self.fetch_val(query, *values)

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: str,
        *where_args,
        returning: Optional[str] = None,
    ) -> str:
        """
        更新记录

        Args:
            table: 表名
            data: 更新数据
            where: WHERE条件
            *where_args: WHERE参数
            returning: 返回字段

        Returns:
            执行状态
        """
        set_clause = [f"{col} = ${i + 1}" for i, col in enumerate(data.keys())]
        set_values = list(data.values())

        query = f"UPDATE {table} SET {', '.join(set_clause)} WHERE {where}"

        if returning:
            query += f" RETURNING {returning}"

        return await self.execute(query, *set_values, *where_args)

    async def delete(
        self, table: str, where: str, *where_args, returning: Optional[str] = None
    ) -> str:
        """
        删除记录

        Args:
            table: 表名
            where: WHERE条件
            *where_args: WHERE参数
            returning: 返回字段

        Returns:
            执行状态
        """
        query = f"DELETE FROM {table} WHERE {where}"

        if returning:
            query += f" RETURNING {returning}"

        return await self.execute(query, *where_args)

    async def count(self, table: str, where: str = "", *args) -> int:
        """
        统计记录数

        Args:
            table: 表名
            where: WHERE条件
            *args: 参数

        Returns:
            记录数
        """
        query = f"SELECT COUNT(*) FROM {table}"
        if where:
            query += f" WHERE {where}"

        result = await self.fetch_val(query, *args)
        return result if result is not None else 0

    async def exists(self, table: str, where: str, *args) -> bool:
        """
        检查记录是否存在

        Args:
            table: 表名
            where: WHERE条件
            *args: 参数

        Returns:
            是否存在
        """
        count = await self.count(table, where, *args)
        return count > 0

    # ===========================
    # 表操作
    # ===========================

    async def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            是否存在
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = $1
            )
        """
        return await self.fetch_val(query, table_name)

    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            列信息列表
        """
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        return await self.fetch_all(query, table_name)

    # ===========================
    # 健康检查
    # ===========================

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            数据库是否健康
        """
        try:
            result = await self.fetch_val("SELECT 1")
            return result == 1
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False


# ===========================
# 全局客户端实例
# ===========================

_postgres_client: Optional[PostgresClient] = None


async def get_postgres_client() -> PostgresClient:
    """获取全局PostgreSQL客户端实例"""
    global _postgres_client

    if _postgres_client is None:
        from ..config import get_settings

        settings = get_settings()
        _postgres_client = PostgresClient(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
        )
        await _postgres_client.connect()

    return _postgres_client
