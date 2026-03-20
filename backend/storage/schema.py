# -*- coding: utf-8 -*-
"""
TDengine 数据库表结构定义

定义所有超级表和创建SQL
"""
from typing import List, Dict, Any
from loguru import logger


class DatabaseSchema:
    """
    数据库表结构管理
    """

    # 数据库名称
    DATABASE_NAME = "quant_db"

    # ===========================
    # 超级表定义
    # ===========================

    SUPER_TABLES = {
        # 股票K线超级表
        "stock_bars": """
            CREATE STABLE IF NOT EXISTS stock_bars (
                ts TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE
            ) TAGS (
                symbol NCHAR(20),
                market NCHAR(4),
                interval NCHAR(10)
            );
        """,

        # 股票行情超级表
        "stock_quotes": """
            CREATE STABLE IF NOT EXISTS stock_quotes (
                ts TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                pre_close DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                change DOUBLE,
                change_percent DOUBLE,
                bid_price1 DOUBLE,
                bid_volume1 DOUBLE,
                ask_price1 DOUBLE,
                ask_volume1 DOUBLE
            ) TAGS (
                symbol NCHAR(20),
                market NCHAR(4)
            );
        """,

        # 股票逐笔成交超级表
        "stock_ticks": """
            CREATE STABLE IF NOT EXISTS stock_ticks (
                ts TIMESTAMP,
                price DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                direction NCHAR(1)
            ) TAGS (
                symbol NCHAR(20),
                market NCHAR(4)
            );
        """,

        # 期货K线超级表
        "futures_bars": """
            CREATE STABLE IF NOT EXISTS futures_bars (
                ts TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                open_interest DOUBLE,
                settlement DOUBLE
            ) TAGS (
                symbol NCHAR(20),
                exchange NCHAR(10),
                interval NCHAR(10)
            );
        """,

        # 期货行情超级表
        "futures_quotes": """
            CREATE STABLE IF NOT EXISTS futures_quotes (
                ts TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                pre_close DOUBLE,
                settlement DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                open_interest DOUBLE,
                change DOUBLE,
                change_percent DOUBLE
            ) TAGS (
                symbol NCHAR(20),
                exchange NCHAR(10)
            );
        """,

        # 期货逐笔成交超级表
        "futures_ticks": """
            CREATE STABLE IF NOT EXISTS futures_ticks (
                ts TIMESTAMP,
                price DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                direction NCHAR(1),
                open_interest DOUBLE
            ) TAGS (
                symbol NCHAR(20),
                exchange NCHAR(10)
            );
        """,

        # 指数K线超级表
        "index_bars": """
            CREATE STABLE IF NOT EXISTS index_bars (
                ts TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE
            ) TAGS (
                symbol NCHAR(20),
                index_type NCHAR(10),
                interval NCHAR(10)
            );
        """,

        # 指数行情超级表
        "index_quotes": """
            CREATE STABLE IF NOT EXISTS index_quotes (
                ts TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                pre_close DOUBLE,
                change DOUBLE,
                change_percent DOUBLE,
                up_count INT,
                down_count INT,
                unchanged_count INT
            ) TAGS (
                symbol NCHAR(20),
                index_type NCHAR(10)
            );
        """,

        # 板块行情超级表
        "sector_quotes": """
            CREATE STABLE IF NOT EXISTS sector_quotes (
                ts TIMESTAMP,
                index_value DOUBLE,
                pre_index DOUBLE,
                change DOUBLE,
                change_percent DOUBLE,
                amount DOUBLE,
                stock_count INT,
                up_count INT,
                down_count INT,
                leader_stock NCHAR(20),
                leader_change DOUBLE
            ) TAGS (
                name NCHAR(50),
                sector_type NCHAR(10)
            );
        """,
    }

    # ===========================
    # 初始化SQL
    # ===========================

    @classmethod
    def get_init_sql(cls) -> str:
        """
        获取数据库初始化SQL

        Returns:
            完整的初始化SQL脚本
        """
        sql_lines = []

        # 创建数据库
        sql_lines.append(f"CREATE DATABASE IF NOT EXISTS {cls.DATABASE_NAME} KEEP 3650 DAYS BUFFER 16;")
        sql_lines.append(f"USE {cls.DATABASE_NAME};")

        # 创建所有超级表
        for table_name, table_sql in cls.SUPER_TABLES.items():
            # 移除末尾的分号（如果有）
            clean_sql = table_sql.strip().rstrip(";")
            sql_lines.append(f"{clean_sql};")

        return "\n".join(sql_lines)

    @classmethod
    def get_create_table_sql(cls, table_name: str) -> str:
        """
        获取创建超级表的SQL

        Args:
            table_name: 表名

        Returns:
            创建SQL
        """
        if table_name not in cls.SUPER_TABLES:
            raise ValueError(f"Unknown table: {table_name}")

        return cls.SUPER_TABLES[table_name].strip()

    @classmethod
    def get_all_table_names(cls) -> List[str]:
        """获取所有超级表名称"""
        return list(cls.SUPER_TABLES.keys())

    # ===========================
    # 表结构信息
    # ===========================

    @classmethod
    def get_table_info(cls, table_name: str) -> Dict[str, Any]:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            表结构信息字典
        """
        table_info = {
            "stock_bars": {
                "description": "股票K线数据",
                "fields": ["ts", "open", "high", "low", "close", "volume", "amount"],
                "tags": ["symbol", "market", "interval"],
                "intervals": ["1min", "5min", "15min", "30min", "60min", "1day", "1week", "1month"],
            },
            "stock_quotes": {
                "description": "股票实时行情",
                "fields": ["ts", "open", "high", "low", "close", "pre_close", "volume", "amount",
                          "change", "change_percent", "bid_price1", "bid_volume1", "ask_price1", "ask_volume1"],
                "tags": ["symbol", "market"],
            },
            "stock_ticks": {
                "description": "股票逐笔成交",
                "fields": ["ts", "price", "volume", "amount", "direction"],
                "tags": ["symbol", "market"],
            },
            "futures_bars": {
                "description": "期货K线数据",
                "fields": ["ts", "open", "high", "low", "close", "volume", "amount", "open_interest", "settlement"],
                "tags": ["symbol", "exchange", "interval"],
                "intervals": ["1min", "5min", "15min", "30min", "60min", "1day", "1week", "1month"],
            },
            "futures_quotes": {
                "description": "期货实时行情",
                "fields": ["ts", "open", "high", "low", "close", "pre_close", "settlement",
                          "volume", "amount", "open_interest", "change", "change_percent"],
                "tags": ["symbol", "exchange"],
            },
            "futures_ticks": {
                "description": "期货逐笔成交",
                "fields": ["ts", "price", "volume", "amount", "direction", "open_interest"],
                "tags": ["symbol", "exchange"],
            },
            "index_bars": {
                "description": "指数K线数据",
                "fields": ["ts", "open", "high", "low", "close", "volume", "amount"],
                "tags": ["symbol", "index_type", "interval"],
                "intervals": ["1min", "5min", "15min", "30min", "60min", "1day", "1week", "1month"],
            },
            "index_quotes": {
                "description": "指数实时行情",
                "fields": ["ts", "open", "high", "low", "close", "pre_close", "change",
                          "change_percent", "up_count", "down_count", "unchanged_count"],
                "tags": ["symbol", "index_type"],
            },
            "sector_quotes": {
                "description": "板块实时行情",
                "fields": ["ts", "index_value", "pre_index", "change", "change_percent",
                          "amount", "stock_count", "up_count", "down_count", "leader_stock", "leader_change"],
                "tags": ["name", "sector_type"],
            },
        }

        if table_name not in table_info:
            raise ValueError(f"Unknown table: {table_name}")

        return table_info[table_name]

    @classmethod
    def get_child_table_name(cls, super_table: str, *tag_values) -> str:
        """
        生成子表名称

        Args:
            super_table: 超级表名
            *tag_values: 标签值

        Returns:
            子表名称
        """
        # 将标签值用下划线连接
        suffix = "_".join(str(v).replace("-", "_").replace(".", "_") for v in tag_values)
        return f"{super_table}_{suffix}"


class SchemaManager:
    """
    数据库表结构管理器

    用于创建和管理TDengine表结构
    """

    def __init__(self, client):
        """
        初始化管理器

        Args:
            client: TDEngine客户端实例
        """
        self.client = client
        self.schema = DatabaseSchema

    async def init_database(self):
        """初始化数据库（创建所有超级表）"""
        sql = self.schema.get_init_sql()

        # 分割SQL语句
        statements = self._split_sql(sql)

        for stmt in statements:
            try:
                await self.client.execute(stmt)
            except Exception as e:
                logger.warning(f"Execute SQL failed (may already exist): {e}")

        logger.info("Database initialized successfully")

    async def create_super_table(self, table_name: str):
        """
        创建单个超级表

        Args:
            table_name: 表名
        """
        sql = self.schema.get_create_table_sql(table_name)
        await self.client.execute(sql)
        logger.info(f"Created super table: {table_name}")

    async def check_tables(self) -> Dict[str, bool]:
        """
        检查所有超级表是否存在

        Returns:
            {表名: 是否存在}
        """
        result = {}
        tables = self.schema.get_all_table_names()

        for table in tables:
            try:
                sql = f"DESC {table}"
                await self.client.query(sql)
                result[table] = True
            except Exception:
                result[table] = False

        return result

    def _split_sql(self, sql: str) -> List[str]:
        """分割SQL语句"""
        # 移除注释
        lines = []
        for line in sql.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("--"):
                lines.append(stripped)

        sql = " ".join(lines)

        # 分割语句
        statements = []
        current = []
        in_string = False

        for char in sql:
            if char == "'":
                in_string = not in_string
            elif char == ";" and not in_string:
                if current:
                    statements.append("".join(current).strip())
                    current = []
                continue

            current.append(char)

        if current:
            statements.append("".join(current).strip())

        return [s for s in statements if s]
