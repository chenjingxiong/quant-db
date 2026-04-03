# -*- coding: utf-8 -*-
"""
TDengine 客户端封装

提供连接管理、批量写入、查询等功能
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
from loguru import logger
import json

# 延迟导入taos以支持可选的TDengine功能
_taos_module = None
_TDAVAILABLE = False

def _get_taos():
    """获取taos模块（延迟导入）"""
    global _taos_module, _TDAVAILABLE
    if _taos_module is not None:
        return _taos_module
    try:
        import taos
        _taos_module = taos
        _TDAVAILABLE = True
        return taos
    except (ImportError, OSError) as e:
        _TDAVAILABLE = False
        logger.warning(f"TDengine not available: {e}")
        return None

def is_tdengine_available():
    """检查TDengine是否可用"""
    if not _TDAVAILABLE:
        _get_taos()
    return _TDAVAILABLE

# 类型注释（仅在类型检查时使用）
if TYPE_CHECKING:
    try:
        from taos import TaosConnection
    except ImportError:
        TaosConnection = object  # type: ignore
else:
    # 运行时使用字符串类型注解
    TaosConnection = object  # type: ignore


from ..config import get_settings
from ..utils.async_helper import get_event_loop


class TDEngineClient:
    """
    TDengine 客户端

    提供异步接口的TDengine操作
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化客户端

        Args:
            config: 配置字典
        """
        if not is_tdengine_available():
            raise ImportError("TDengine client library is not available")

        self.settings = get_settings()

        # 连接配置
        self.host = self.settings.tdengine_host
        self.port = self.settings.tdengine_port
        self.user = self.settings.tdengine_user
        self.password = self.settings.tdengine_password
        self.database = self.settings.tdengine_database

        # 连接池
        self._connections: List["TaosConnection"] = []
        self._max_connections = 10
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
            conn = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: taos.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                )
            )

            async with self._lock:
                self._connections.append(conn)

            logger.info(f"Connected to TDengine: {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to TDengine: {e}")
            return False

    async def disconnect(self):
        """断开所有连接"""
        async with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()

        logger.info("Disconnected from TDengine")

    async def _get_connection(self) -> "TaosConnection":
        """获取一个连接"""
        async with self._lock:
            if self._connections:
                return self._connections[0]

        # 如果没有连接，创建一个新的
        await self.connect()
        async with self._lock:
            return self._connections[0]

    async def execute(self, sql: str, params: Optional[Tuple] = None) -> Any:
        """
        执行SQL语句

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            执行结果
        """
        try:
            conn = await self._get_connection()

            if params:
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: conn.execute(sql, params)
                )
            else:
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: conn.execute(sql)
                )

            return result

        except Exception as e:
            logger.error(f"Execute SQL failed: {e}\nSQL: {sql}")
            self.stats["errors"] += 1
            raise

    async def execute_many(self, sql: str, params_list: List[Tuple]) -> Any:
        """
        批量执行SQL

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            执行结果
        """
        try:
            conn = await self._get_connection()
            loop = get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: conn.execute_many(sql, params_list)
            )

            return result

        except Exception as e:
            logger.error(f"Execute many SQL failed: {e}")
            self.stats["errors"] += 1
            raise

    async def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
        """
        查询数据

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            查询结果列表
        """
        try:
            conn = await self._get_connection()

            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: conn.query(sql)
            )

            # 转换为字典列表
            data = []
            if result:
                columns = [field.name for field in result.fields]
                for row in result:
                    data.append(dict(zip(columns, row)))

            self.stats["total_queried"] += len(data)
            return data

        except Exception as e:
            logger.error(f"Query failed: {e}\nSQL: {sql}")
            self.stats["errors"] += 1
            return []

    async def insert_stock_quote(self, quote: Dict) -> bool:
        """
        插入股票行情

        Args:
            quote: 行情数据

        Returns:
            是否成功
        """
        try:
            # 确定表名
            symbol = quote.get("symbol", "")
            table_name = f"stock_quotes_{symbol}"

            # 准备数据
            ts = self._format_timestamp(quote.get("ts"))
            tags = (
                quote.get("symbol", ""),
                quote.get("market", "SZ"),
            )

            fields = (
                ts,
                quote.get("open"),
                quote.get("high"),
                quote.get("low"),
                quote.get("close"),
                quote.get("pre_close"),
                quote.get("volume"),
                quote.get("amount"),
                quote.get("change"),
                quote.get("change_percent"),
                quote.get("bid_price1"),
                quote.get("bid_volume1"),
                quote.get("ask_price1"),
                quote.get("ask_volume1"),
            )

            # 构建SQL
            sql = f"""
                INSERT INTO {table_name} USING stock_quotes TAGS (?, ?)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            await self.execute(sql, tags + fields)
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
            # 按symbol分组
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

                # 准备批量数据
                params_list = []
                for bar in symbol_bars:
                    ts = self._format_timestamp(bar.get("ts"))
                    tags = (symbol, bar.get("market", "SZ"), interval)
                    fields = (
                        ts,
                        bar.get("open"),
                        bar.get("high"),
                        bar.get("low"),
                        bar.get("close"),
                        bar.get("volume"),
                        bar.get("amount"),
                    )
                    params_list.append(tags + fields)

                # 批量插入
                sql = f"""
                    INSERT INTO {table_name} USING stock_bars TAGS (?, ?, ?)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                await self.execute_many(sql, params_list)
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
            tags = (
                symbol,
                quote.get("exchange", "CFFEX"),
            )

            fields = (
                ts,
                quote.get("open"),
                quote.get("high"),
                quote.get("low"),
                quote.get("close"),
                quote.get("pre_close"),
                quote.get("settlement"),
                quote.get("volume"),
                quote.get("amount"),
                quote.get("open_interest"),
                quote.get("change"),
                quote.get("change_percent"),
            )

            sql = f"""
                INSERT INTO {table_name} USING futures_quotes TAGS (?, ?)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            await self.execute(sql, tags + fields)
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

                params_list = []
                for bar in symbol_bars:
                    ts = self._format_timestamp(bar.get("ts"))
                    tags = (symbol, bar.get("exchange", "CFFEX"), interval)
                    fields = (
                        ts,
                        bar.get("open"),
                        bar.get("high"),
                        bar.get("low"),
                        bar.get("close"),
                        bar.get("volume"),
                        bar.get("amount"),
                        bar.get("open_interest"),
                        bar.get("settlement"),
                    )
                    params_list.append(tags + fields)

                sql = f"""
                    INSERT INTO {table_name} USING futures_bars TAGS (?, ?, ?)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                await self.execute_many(sql, params_list)
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

        sql = f"SELECT * FROM {table_name} WHERE interval = '{interval}'"

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
        # Validate symbol to prevent injection
        if not symbol.replace("_", "").replace("-", "").isalnum():
            logger.warning(f"Invalid futures symbol: {symbol}")
            return []

        table_name = f"futures_bars_{symbol}"
        sql = f"SELECT * FROM {table_name} WHERE interval = ?"

        params = [interval]
        if start_time:
            sql += " AND ts >= ?"
            params.append(self._format_timestamp(start_time))
        if end_time:
            sql += " AND ts <= ?"
            params.append(self._format_timestamp(end_time))

        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(str(limit))

        return await self.query(sql, tuple(params))

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
        """切换数据库"""
        sql = f"USE {database}"
        await self.execute(sql)
        logger.info(f"Switched to database: {database}")

    async def create_database(self, database: str, keep: int = 3650):
        """
        创建数据库

        Args:
            database: 数据库名
            keep: 数据保留天数
        """
        sql = f"CREATE DATABASE IF NOT EXISTS {database} KEEP {keep} DAYS BUFFER 16"
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
