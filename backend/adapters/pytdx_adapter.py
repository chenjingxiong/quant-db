# -*- coding: utf-8 -*-
"""
pytdx 数据源适配器

通达信数据源是目前国内最常用的免费行情数据源之一
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

try:
    from pytdx.hq import TdxHq_API
    from pytdx.params import TDXParams
    PYTDX_AVAILABLE = True
except ImportError:
    PYTDX_AVAILABLE = False
    TDXParams = None
    TdxHq_API = None
    logger.warning("pytdx not installed, install with: pip install pytdx")

from .base import BaseAdapter, Quote, Bar, Tick
from ..utils.async_helper import get_event_loop


class PytdxAdapter(BaseAdapter):
    """
    pytdx 通达信数据源适配器

    支持功能:
    - 股票实时行情
    - 期货实时行情
    - K线数据
    - 股票列表
    """

    # 通达信市场代码映射
    MARKET_SH = 1  # 上海
    MARKET_SZ = 0  # 深圳

    # K线周期映射
    INTERVAL_MAP = {
        "1min": 9,    # 1分钟
        "5min": 0,    # 5分钟
        "15min": 1,   # 15分钟
        "30min": 2,   # 30分钟
        "60min": 3,   # 60分钟
        "1h": 3,      # 1小时
        "1day": 5,    # 日K
        "1week": 6,   # 周K
        "1month": 7,  # 月K
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if not PYTDX_AVAILABLE:
            raise ImportError("pytdx is not installed")

        # 配置
        self.hosts = self.config.get("hosts", ["119.147.212.81"])
        self.port = self.config.get("port", 7709)
        self.time_out = self.config.get("timeout", 5)

        # 连接状态
        self.api: Optional["TdxHq_API"] = None
        self.current_host = None
        self.current_market_id = 0

    async def connect(self) -> bool:
        """连接通达信服务器"""
        try:
            if self.api:
                await self.disconnect()

            self.api = TdxHq_API(raise_exception=True)

            # 尝试连接可用的服务器
            for host in self.hosts:
                try:
                    # 在线程池中执行同步连接
                    result = await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: self.api.connect(host, self.port, time_out=self.time_out)
                    )

                    if result:
                        self.current_host = host
                        self.is_connected = True
                        logger.info(f"{self.name}: connected to {host}:{self.port}")
                        return True

                except Exception as e:
                    logger.debug(f"{self.name}: failed to connect {host} - {e}")
                    continue

            logger.error(f"{self.name}: all connection attempts failed")
            self.is_connected = False
            return False

        except Exception as e:
            logger.error(f"{self.name}: connect error - {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """断开连接"""
        try:
            if self.api:
                await asyncio.get_running_loop().run_in_executor(None, self.api.disconnect)
                self.api = None
            self.is_connected = False
            logger.info(f"{self.name}: disconnected")
        except Exception as e:
            logger.error(f"{self.name}: disconnect error - {e}")

    def _ensure_connected(self):
        """确保已连接"""
        if not self.is_connected or not self.api:
            raise ConnectionError(f"{self.name}: not connected")

    def _parse_symbol(self, symbol: str) -> tuple:
        """
        解析股票代码

        Args:
            symbol: 股票代码，如 000001, 600000, sh000001, sz000001

        Returns:
            (market, code): (市场代码, 股票代码)
        """
        symbol = symbol.upper().strip()

        # 处理带市场前缀的代码
        if symbol.startswith("SH"):
            return self.MARKET_SH, symbol[2:]
        elif symbol.startswith("SZ"):
            return self.MARKET_SZ, symbol[2:]

        # 根据代码前缀判断市场
        if symbol.startswith("6"):
            return self.MARKET_SH, symbol
        elif symbol.startswith(("0", "3")):
            return self.MARKET_SZ, symbol
        else:
            # 默认深圳
            return self.MARKET_SZ, symbol

    async def get_stock_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取股票实时行情"""
        try:
            self._ensure_connected()

            # 转换为通达信格式
            tdx_symbols = []
            for symbol in symbols:
                market, code = self._parse_symbol(symbol)
                tdx_symbols.append((market, code))

            # 分批查询（通达信一次最多800只）
            batch_size = 800
            all_quotes = []

            loop = get_event_loop()

            for i in range(0, len(tdx_symbols), batch_size):
                batch = tdx_symbols[i:i + batch_size]
                data = await loop.run_in_executor(
                    None,
                    lambda: self.api.get_security_quotes(batch)
                )
                all_quotes.extend(data or [])

            # 转换为Quote格式
            quotes = []
            now = datetime.now()

            for item in all_quotes:
                try:
                    # 代码格式化
                    code = item["code"]
                    market = "SH" if item["market"] == self.MARKET_SH else "SZ"
                    symbol = f"{market}{code}"

                    quotes.append(Quote(
                        symbol=symbol,
                        ts=now,
                        open=float(item["price_open"]) if item["price_open"] > 0 else None,
                        high=float(item["price_high"]) if item["price_high"] > 0 else None,
                        low=float(item["price_low"]) if item["price_low"] > 0 else None,
                        close=float(item["price_current"]) if item["price_current"] > 0 else None,
                        pre_close=float(item["price_last_close"]) if item["price_last_close"] > 0 else None,
                        volume=float(item["vol"]) if item["vol"] > 0 else None,
                        amount=float(item["amount"]) if item["amount"] > 0 else None,
                        change=float(item["price_change"]) if item.get("price_change") else None,
                        change_percent=float(item["price_change_rate"]) if item.get("price_change_rate") else None,
                        extra={
                            "name": item.get("name", ""),
                            "bid1": float(item["bid1"]) if item.get("bid1", 0) > 0 else None,
                            "bid_vol1": float(item["bid1_volume"]) if item.get("bid1_volume", 0) > 0 else None,
                            "ask1": float(item["ask1"]) if item.get("ask1", 0) > 0 else None,
                            "ask_vol1": float(item["ask1_volume"]) if item.get("ask1_volume", 0) > 0 else None,
                        }
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse quote error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(quotes)} stock quotes")
            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_stock_quotes error - {e}")
            return []

    async def get_futures_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取期货实时行情"""
        # pytdx也支持期货行情，使用类似的接口
        try:
            self._ensure_connected()

            # 期货市场代码
            MARKET_CFFEX = 47  # 中金所
            MARKET_SHFE = 48   # 上期所
            MARKET_DCE = 49    # 大商所
            MARKET_CZCE = 50   # 郑商所

            # 根据代码判断期货交易所
            def get_future_market(symbol: str) -> int:
                s = symbol.upper()
                if s.startswith(("IF", "IH", "IC", "IM", "T", "TF", "TS", "TL")):
                    return MARKET_CFFEX
                elif s.startswith(("AU", "AG", "CU", "AL", "ZN", "PB", "NI", "SN", "RB", "HC", "SS", "WR", "SP")):
                    return MARKET_SHFE
                elif s.startswith(("I", "JM", "J", "A", "B", "M", "Y", "P", "L", "PP", "V", "EB", "EG", "PG")):
                    return MARKET_DCE
                elif s.startswith(("SR", "CF", "TA", "MA", "RM", "OI", "ZC", "FG", "UR", "SA", "AP", "CJ", "PK", "SF", "SM")):
                    return MARKET_CZCE
                return MARKET_CFFEX  # 默认

            # 转换格式
            tdx_symbols = [(get_future_market(s), s) for s in symbols]

            loop = get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_quotes(tdx_symbols)
            )

            quotes = []
            now = datetime.now()

            for item in data or []:
                try:
                    quotes.append(Quote(
                        symbol=item["code"],
                        ts=now,
                        open=float(item["price_open"]) if item["price_open"] > 0 else None,
                        high=float(item["price_high"]) if item["price_high"] > 0 else None,
                        low=float(item["price_low"]) if item["price_low"] > 0 else None,
                        close=float(item["price_current"]) if item["price_current"] > 0 else None,
                        volume=float(item["vol"]) if item["vol"] > 0 else None,
                        amount=float(item["amount"]) if item["amount"] > 0 else None,
                        extra={"name": item.get("name", "")}
                    ))
                except Exception:
                    continue

            logger.debug(f"{self.name}: got {len(quotes)} futures quotes")
            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_futures_quotes error - {e}")
            return []

    async def get_stock_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取股票K线数据"""
        try:
            self._ensure_connected()

            # 解析周期
            kline_type = self.INTERVAL_MAP.get(interval)
            if kline_type is None:
                logger.warning(f"{self.name}: unsupported interval {interval}")
                return []

            market, code = self._parse_symbol(symbol)

            loop = get_event_loop()

            # 获取K线数据
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_bars(
                    kline_type,
                    market,
                    code,
                    start=0,
                    count=limit
                )
            )

            bars = []
            for item in reversed(data or []):  # pytdx返回的是倒序的
                try:
                    # 解析时间
                    dt = datetime.strptime(item["datetime"], "%Y-%m-%d %H:%M:%S")

                    # 时间范围过滤
                    if start_time and dt < start_time:
                        continue
                    if end_time and dt > end_time:
                        continue

                    bars.append(Bar(
                        symbol=symbol,
                        interval=interval,
                        ts=dt,
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                        volume=float(item["vol"]),
                        amount=float(item.get("amount", 0))
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse bar error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(bars)} bars for {symbol}")
            return bars

        except Exception as e:
            logger.error(f"{self.name}: get_stock_bars error - {e}")
            return []

    async def get_futures_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取期货K线数据"""
        # 期货K线获取逻辑与股票类似
        return await self.get_stock_bars(symbol, interval, start_time, end_time, limit)

    async def get_stock_ticks(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Tick]:
        """获取股票逐笔成交"""
        try:
            self._ensure_connected()

            market, code = self._parse_symbol(symbol)

            loop = get_event_loop()

            # 获取历史分笔成交
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_history_transaction_data(
                    market,
                    code,
                    start=0,
                    count=limit
                )
            )

            ticks = []
            for item in data or []:
                try:
                    dt = datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")

                    if start_time and dt < start_time:
                        continue
                    if end_time and dt > end_time:
                        continue

                    # 判断买卖方向
                    direction = "B" if item["buyorsell"] == 1 else "S"

                    ticks.append(Tick(
                        symbol=symbol,
                        ts=dt,
                        price=float(item["price"]),
                        volume=float(item["vol"]),
                        amount=float(item["amount"]),
                        direction=direction
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse tick error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(ticks)} ticks for {symbol}")
            return ticks

        except Exception as e:
            logger.error(f"{self.name}: get_stock_ticks error - {e}")
            return []

    async def get_all_stock_list(self) -> List[Dict[str, Any]]:
        """获取所有股票列表"""
        try:
            self._ensure_connected()

            loop = get_event_loop()

            # 获取上海股票列表
            sh_stocks = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_list(self.MARKET_SH, 0)
            )

            # 获取深圳股票列表
            sz_stocks = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_list(self.MARKET_SZ, 0)
            )

            stocks = []

            for item in (sh_stocks or []):
                stocks.append({
                    "symbol": f"SH{item['code']}",
                    "code": item["code"],
                    "name": item.get("name", ""),
                    "market": "SH"
                })

            for item in (sz_stocks or []):
                stocks.append({
                    "symbol": f"SZ{item['code']}",
                    "code": item["code"],
                    "name": item.get("name", ""),
                    "market": "SZ"
                })

            logger.info(f"{self.name}: got {len(stocks)} stocks")
            return stocks

        except Exception as e:
            logger.error(f"{self.name}: get_all_stock_list error - {e}")
            return []

    async def get_all_futures_list(self) -> List[Dict[str, Any]]:
        """获取所有期货合约列表"""
        # pytdx获取期货合约列表的方法类似
        # 这里简化返回
        return []

    async def get_index_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取指数实时行情"""
        # 指数行情获取方式与股票类似
        return await self.get_stock_quotes(symbols)
