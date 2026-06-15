# -*- coding: utf-8 -*-
"""
TDengine 客户端封装 (REST API 模式)

使用 taosrest 通过 HTTP 接口连接 TDengine，避免原生 C 驱动的 exec-stack 限制
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

# 延迟导入 taosrest
_taosrest_module = None
_TDAVAILABLE = False


def _get_taosrest():
    """获取 taosrest 模块（延迟导入）"""
    global _taosrest_module, _TDAVAILABLE
    if _taosrest_module is not None:
        return _taosrest_module
    try:
        import taosrest
        _taosrest_module = taosrest
        _TDAVAILABLE = True
        return taosrest
    except Exception as e:
        _TDAVAILABLE = False
        logger.warning(f"TDengine REST driver not available: {e}")
        return None


def is_tdengine_available():
    """检查 TDengine REST 驱动是否可用"""
    if not _TDAVAILABLE:
        _get_taosrest()
    return _TDAVAILABLE


from ..config import get_settings


class TDEngineClient:
    """
    TDengine 客户端 (REST API 模式)

    通过 taosrest 连接 TDengine REST 接口 (端口 6041)
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化客户端

        Args:
            config: 配置字典
        """
        if not is_tdengine_available():
            raise ImportError("TDengine REST client library (taosrest) is not available")

        self.settings = get_settings()

        # 连接配置
        self.host = self.settings.tdengine_host
        self.rest_port = self.settings.tdengine_rest_port
        self.user = self.settings.tdengine_user
        self.password = self.settings.tdengine_password
        self.database = self.settings.tdengine_database

        # REST 连接
        self._connection = None
        self._lock = asyncio.Lock()

        # 批量写入配置
        self._batch_buffer: List[Dict] = []
        self._batch_size = 1000
        self._batch_timeout = 5.0

        # 统计
        self.stats = {
            "total_inserted": 0,
            "total_queried": 0,
            "errors": 0,
        }

    async def connect(self) -> bool:
        """
        建立连接

        Returns:
            是否成功
        """
        try:
            taosrest = _get_taosrest()
            url = f"http://{self.host}:{self.rest_port}"

            conn = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: taosrest.connect(
                    url=url,
                    user=self.user,
                    password=self.password,
                )
            )

            async with self._lock:
                self._connection = conn

            logger.info(f"Connected to TDengine REST API: {self.host}:{self.rest_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to TDengine REST API: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        async with self._lock:
            if self._connection:
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None

        logger.info("Disconnected from TDengine")

    async def _get_connection(self):
        """获取连接"""
        async with self._lock:
            if self._connection is not None:
                return self._connection

        # 如果没有连接，创建一个新的
        await self.connect()
        async with self._lock:
            return self._connection

    async def execute(self, sql: str, params: Optional[Tuple] = None) -> Any:
        """
        执行 SQL 语句

        Args:
            sql: SQL 语句
            params: 参数（REST 模式下使用字符串格式化）

        Returns:
            执行结果
        """
        try:
            conn = await self._get_connection()

            if params:
                sql = self._bind_params(sql, params)

            # REST 模式下自动在表操作 SQL 中添加数据库名前缀
            sql = self._qualify_sql(sql)

            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self._execute_sql(conn, sql)
            )

            return result

        except Exception as e:
            logger.error(f"Execute SQL failed: {e}\nSQL: {sql}")
            self.stats["errors"] += 1
            raise

    def _execute_sql(self, conn, sql: str) -> Any:
        """在 executor 中执行 SQL"""
        # REST 模式下 USE 无意义，跳过
        if sql.strip().upper().startswith("USE "):
            return None
        cursor = conn.cursor()
        cursor.execute(sql)
        try:
            return cursor.rowcount
        except Exception:
            return None

    def _qualify_sql(self, sql: str) -> str:
        """
        为 SQL 语句自动添加数据库名前缀（REST 模式无会话状态）

        仅对需要数据库上下文的 SQL 进行处理：
        - CREATE STABLE → CREATE STABLE db.table
        - INSERT INTO t USING stable → INSERT INTO db.t USING db.stable
        - SELECT * FROM → SELECT * FROM db.table
        - USE database → 跳过（已在 use_database 中处理）
        - CREATE DATABASE → 跳过
        - SHOW → 跳过
        """
        if not self.database:
            return sql

        upper = sql.strip().upper()

        # 跳过不需要限定的语句
        if upper.startswith(("CREATE DATABASE", "USE ", "SHOW ", "SELECT 1", "DROP ")):
            return sql

        import re

        db = re.escape(self.database)

        # CREATE STABLE IF NOT EXISTS table_name → CREATE STABLE IF NOT EXISTS db.table_name
        if "CREATE STABLE" in upper:
            sql = re.sub(
                rf'(CREATE\s+STABLE\s+IF\s+NOT\s+EXISTS\s+)(?!{db}\.)(\w+)',
                rf'\1{self.database}.\2',
                sql,
                flags=re.IGNORECASE
            )
            return sql

        # INSERT INTO t [USING stable] → INSERT INTO db.t [USING db.stable]
        if upper.startswith("INSERT"):
            # Qualify the USING supertable first
            sql = re.sub(
                rf'(USING\s+)(?!{db}\.)(\w+)',
                rf'\1{self.database}.\2',
                sql,
                flags=re.IGNORECASE
            )
            # Then qualify the INSERT INTO target table
            sql = re.sub(
                rf'(INSERT\s+INTO\s+)(?!{db}\.)(\w+)',
                rf'\1{self.database}.\2',
                sql,
                flags=re.IGNORECASE
            )
            return sql

        # SELECT ... FROM table_name → SELECT ... FROM db.table_name
        if upper.startswith("SELECT"):
            sql = re.sub(
                rf'(FROM\s+)(?!{db}\.)(\w+)',
                rf'\1{self.database}.\2',
                sql,
                flags=re.IGNORECASE
            )
            return sql

        return sql

    def _bind_params(self, sql: str, params: Tuple) -> str:
        """
        将参数绑定到 SQL（REST 模式不支持 ? 占位符，改用字符串格式化）

        Args:
            sql: 带 ? 占位符的 SQL
            params: 参数元组

        Returns:
            格式化后的 SQL
        """
        for param in params:
            if isinstance(param, str):
                value = f"'{param}'"
            elif isinstance(param, (int, float)):
                value = str(param)
            elif param is None:
                value = "NULL"
            else:
                value = f"'{param}'"
            sql = sql.replace("?", value, 1)
        return sql

    async def execute_many(self, sql: str, params_list: List[Tuple]) -> Any:
        """
        批量执行 SQL

        Args:
            sql: SQL 语句
            params_list: 参数列表

        Returns:
            执行结果
        """
        try:
            conn = await self._get_connection()

            # REST 模式：逐条执行
            results = []
            for params in params_list:
                formatted_sql = self._bind_params(sql, params)
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda s=formatted_sql: self._execute_sql(conn, s)
                )
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Execute many SQL failed: {e}")
            self.stats["errors"] += 1
            raise

    async def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
        """
        查询数据

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            查询结果列表
        """
        try:
            conn = await self._get_connection()

            if params:
                sql = self._bind_params(sql, params)

            # REST 模式下自动在表操作 SQL 中添加数据库名前缀
            sql = self._qualify_sql(sql)

            data = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self._query_sql(conn, sql)
            )

            self.stats["total_queried"] += len(data)
            return data

        except Exception as e:
            logger.error(f"Query failed: {e}\nSQL: {sql}")
            self.stats["errors"] += 1
            return []

    def _query_sql(self, conn, sql: str) -> List[Dict]:
        """在 executor 中执行查询"""
        cursor = conn.cursor()
        cursor.execute(sql)

        # 获取列名
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # 获取数据
        rows = cursor.fetchall()

        # 转换为字典列表
        data = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i] if i < len(row) else None
                # 处理 datetime 对象的序列化
                if isinstance(val, datetime):
                    val = val.isoformat()
                row_dict[col] = val
            data.append(row_dict)

        return data

    async def insert_stock_quote(self, quote: Dict) -> bool:
        """
        插入股票行情

        Args:
            quote: 行情数据

        Returns:
            是否成功
        """
        try:
            symbol = quote.get("symbol", "")
            table_name = f"stock_quotes_{symbol}"

            ts = self._format_timestamp(quote.get("ts"))

            sql = (
                f"INSERT INTO {table_name} USING stock_quotes TAGS "
                f"('{quote.get('symbol', '')}', '{quote.get('market', 'SZ')}') "
                f"VALUES ('{ts}', "
                f"{quote.get('open', 'NULL')}, "
                f"{quote.get('high', 'NULL')}, "
                f"{quote.get('low', 'NULL')}, "
                f"{quote.get('close', 'NULL')}, "
                f"{quote.get('pre_close', 'NULL')}, "
                f"{quote.get('volume', 'NULL')}, "
                f"{quote.get('amount', 'NULL')}, "
                f"{quote.get('change', 'NULL')}, "
                f"{quote.get('change_percent', 'NULL')}, "
                f"{quote.get('bid_price1', 'NULL')}, "
                f"{quote.get('bid_volume1', 'NULL')}, "
                f"{quote.get('ask_price1', 'NULL')}, "
                f"{quote.get('ask_volume1', 'NULL')})"
            )

            await self.execute(sql)
            self.stats["total_inserted"] += 1
            return True

        except Exception as e:
            logger.error(f"Insert stock quote failed: {e}")
            return False

    async def insert_stock_bars(self, bars: List[Dict]) -> int:
        """
        批量插入股票K线

        Args:
            bars: K线数据列表

        Returns:
            成功插入的数量
        """
        if not bars:
            return 0

        try:
            grouped: Dict[str, List[Dict]] = {}
            for bar in bars:
                symbol = bar.get("symbol", "")
                if symbol:
                    if symbol not in grouped:
                        grouped[symbol] = []
                    grouped[symbol].append(bar)

            total_inserted = 0

            for symbol, symbol_bars in grouped.items():
                table_name = f"stock_bars_{symbol}"
                interval = symbol_bars[0].get("interval", "1min")

                # 构建 VALUES 子句
                values_parts = []
                for bar in symbol_bars:
                    ts = self._format_timestamp(bar.get("ts"))
                    values_parts.append(
                        f"('{ts}', "
                        f"{bar.get('open', 'NULL')}, "
                        f"{bar.get('high', 'NULL')}, "
                        f"{bar.get('low', 'NULL')}, "
                        f"{bar.get('close', 'NULL')}, "
                        f"{bar.get('volume', 'NULL')}, "
                        f"{bar.get('amount', 'NULL')})"
                    )

                sql = (
                    f"INSERT INTO {table_name} USING stock_bars TAGS "
                    f"('{symbol}', '{bar.get('market', 'SZ')}', '{interval}') "
                    f"VALUES {', '.join(values_parts)}"
                )

                await self.execute(sql)
                total_inserted += len(symbol_bars)

            self.stats["total_inserted"] += total_inserted
            return total_inserted

        except Exception as e:
            logger.error(f"Insert stock bars failed: {e}")
            return 0

    async def insert_futures_quote(self, quote: Dict) -> bool:
        """
        插入期货行情

        Args:
            quote: 行情数据

        Returns:
            是否成功
        """
        try:
            symbol = quote.get("symbol", "")
            table_name = f"futures_quotes_{symbol}"

            ts = self._format_timestamp(quote.get("ts"))

            sql = (
                f"INSERT INTO {table_name} USING futures_quotes TAGS "
                f"('{symbol}', '{quote.get('exchange', 'CFFEX')}') "
                f"VALUES ('{ts}', "
                f"{quote.get('open', 'NULL')}, "
                f"{quote.get('high', 'NULL')}, "
                f"{quote.get('low', 'NULL')}, "
                f"{quote.get('close', 'NULL')}, "
                f"{quote.get('pre_close', 'NULL')}, "
                f"{quote.get('settlement', 'NULL')}, "
                f"{quote.get('volume', 'NULL')}, "
                f"{quote.get('amount', 'NULL')}, "
                f"{quote.get('open_interest', 'NULL')}, "
                f"{quote.get('change', 'NULL')}, "
                f"{quote.get('change_percent', 'NULL')})"
            )

            await self.execute(sql)
            self.stats["total_inserted"] += 1
            return True

        except Exception as e:
            logger.error(f"Insert futures quote failed: {e}")
            return False

    async def insert_futures_bars(self, bars: List[Dict]) -> int:
        """
        批量插入期货K线

        Args:
            bars: K线数据列表

        Returns:
            成功插入的数量
        """
        if not bars:
            return 0

        try:
            grouped: Dict[str, List[Dict]] = {}
            for bar in bars:
                symbol = bar.get("symbol", "")
                if symbol:
                    if symbol not in grouped:
                        grouped[symbol] = []
                    grouped[symbol].append(bar)

            total_inserted = 0

            for symbol, symbol_bars in grouped.items():
                table_name = f"futures_bars_{symbol}"
                interval = symbol_bars[0].get("interval", "1min")

                values_parts = []
                for bar in symbol_bars:
                    ts = self._format_timestamp(bar.get("ts"))
                    values_parts.append(
                        f"('{ts}', "
                        f"{bar.get('open', 'NULL')}, "
                        f"{bar.get('high', 'NULL')}, "
                        f"{bar.get('low', 'NULL')}, "
                        f"{bar.get('close', 'NULL')}, "
                        f"{bar.get('volume', 'NULL')}, "
                        f"{bar.get('amount', 'NULL')}, "
                        f"{bar.get('open_interest', 'NULL')}, "
                        f"{bar.get('settlement', 'NULL')})"
                    )

                sql = (
                    f"INSERT INTO {table_name} USING futures_bars TAGS "
                    f"('{symbol}', '{bar.get('exchange', 'CFFEX')}', '{interval}') "
                    f"VALUES {', '.join(values_parts)}"
                )

                await self.execute(sql)
                total_inserted += len(symbol_bars)

            self.stats["total_inserted"] += total_inserted
            return total_inserted

        except Exception as e:
            logger.error(f"Insert futures bars failed: {e}")
            return 0

    async def query_stock_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        查询股票K线

        Args:
            symbol: 股票代码
            interval: 周期
            start_time: 开始时间
            end_time: 结束时间
            limit: 数量限制

        Returns:
            K线数据列表
        """
        table_name = f"stock_bars_{symbol}"

        sql = f"SELECT * FROM {table_name} WHERE `interval` = '{interval}'"

        if start_time:
            sql += f" AND ts >= '{self._format_timestamp(start_time)}'"
        if end_time:
            sql += f" AND ts <= '{self._format_timestamp(end_time)}'"

        sql += f" ORDER BY ts DESC LIMIT {limit}"

        return await self.query(sql)

    async def query_stock_quote_latest(self, symbol: str) -> Optional[Dict]:
        """
        查询股票最新行情

        Args:
            symbol: 股票代码

        Returns:
            行情数据
        """
        table_name = f"stock_quotes_{symbol}"
        sql = f"SELECT * FROM {table_name} ORDER BY ts DESC LIMIT 1"

        result = await self.query(sql)
        return result[0] if result else None

    def _format_timestamp(self, ts: Any) -> str:
        """格式化时间戳"""
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        elif isinstance(ts, str):
            return ts
        else:
            return str(ts)

    async def query_futures_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """
        查询期货K线

        Args:
            symbol: 合约代码
            interval: 周期
            start_time: 开始时间
            end_time: 结束时间
            limit: 数量限制

        Returns:
            K线数据列表
        """
        if not symbol.replace("_", "").replace("-", "").isalnum():
            logger.warning(f"Invalid futures symbol: {symbol}")
            return []

        table_name = f"futures_bars_{symbol}"
        sql = f"SELECT * FROM {table_name} WHERE `interval` = '{interval}'"

        if start_time:
            sql += f" AND ts >= '{self._format_timestamp(start_time)}'"
        if end_time:
            sql += f" AND ts <= '{self._format_timestamp(end_time)}'"

        sql += f" ORDER BY ts DESC LIMIT {limit}"

        return await self.query(sql)

    async def query_futures_quote_latest(self, symbol: str) -> Optional[Dict]:
        """
        查询期货最新行情

        Args:
            symbol: 合约代码

        Returns:
            行情数据
        """
        if not symbol.replace("_", "").replace("-", "").isalnum():
            logger.warning(f"Invalid futures symbol: {symbol}")
            return None

        table_name = f"futures_quotes_{symbol}"
        sql = f"SELECT * FROM {table_name} ORDER BY ts DESC LIMIT 1"

        result = await self.query(sql)
        return result[0] if result else None

    async def use_database(self, database: str):
        """切换数据库（REST 模式下记录当前数据库，后续 SQL 自动添加前缀）"""
        self.database = database
        logger.info(f"Switched to database: {database}")

    async def create_database(self, database: str, keep: int = 3650):
        """
        创建数据库

        Args:
            database: 数据库名
            keep: 数据保留天数
        """
        sql = f"CREATE DATABASE IF NOT EXISTS {database} KEEP {keep}"
        await self.execute(sql)
        logger.info(f"Created database: {database}")

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            result = await self.query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_inserted": 0,
            "total_queried": 0,
            "errors": 0,
        }
