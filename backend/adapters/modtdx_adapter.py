# -*- coding: utf-8 -*-
"""
modtdx 数据源适配器

modtdx是通达信的修改版本，提供更多功能和更好的性能
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from .base import BaseAdapter, Quote, Bar, Tick
from ..utils.async_helper import get_event_loop


class ModtdxAdapter(BaseAdapter):
    """
    modtdx 数据源适配器

    注意: modtdx需要从源码安装或使用本地文件
    如果没有安装，此类将无法正常工作
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 尝试导入modtdx
        try:
            from modtdx import ModTdxParams
            self.MODTDX_AVAILABLE = True
        except ImportError:
            self.MODTDX_AVAILABLE = False
            logger.warning("modtdx not installed")

        # 配置
        self.hosts = self.config.get("hosts", ["119.147.212.81"])
        self.port = self.config.get("port", 7709)
        self.timeout = self.config.get("timeout", 5)

        # 连接对象
        self.api = None
        self.current_host = None

    async def connect(self) -> bool:
        """连接modtdx服务器"""
        if not self.MODTDX_AVAILABLE:
            logger.warning(f"{self.name}: modtdx not available, falling back to pytdx")
            return False

        try:
            from modtdx.hq import TdxHq_API

            if self.api:
                await self.disconnect()

            self.api = TdxHq_API(raise_exception=True, auto_retry=True)

            for host in self.hosts:
                try:
                    result = await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: self.api.connect(host, self.port, time_out=self.timeout)
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
            return False

        except Exception as e:
            logger.error(f"{self.name}: connect error - {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        if self.api:
            try:
                await asyncio.get_running_loop().run_in_executor(None, self.api.disconnect)
            except Exception as e:
                logger.error(f"{self.name}: disconnect error - {e}")
            finally:
                self.api = None
        self.is_connected = False

    async def get_stock_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取股票实时行情"""
        if not self.is_connected or not self.api:
            return []

        try:
            # modtdx的API与pytdx类似
            # 这里简化处理，实际使用时需要根据modtdx的具体API调整
            loop = get_event_loop()

            # 转换符号格式
            tdx_symbols = []
            for symbol in symbols:
                # 解析市场
                if symbol.upper().startswith("SH") or symbol.startswith("6"):
                    market = 1
                    code = symbol.replace("SH", "").replace("sh", "")
                else:
                    market = 0
                    code = symbol.replace("SZ", "").replace("sz", "")
                tdx_symbols.append((market, code))

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
                    ))
                except Exception:
                    continue

            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_stock_quotes error - {e}")
            return []

    async def get_futures_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取期货实时行情"""
        # 实现与股票类似
        return await self.get_stock_quotes(symbols)

    async def get_stock_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取股票K线数据"""
        if not self.is_connected or not self.api:
            return []

        try:
            # K线周期映射
            interval_map = {
                "1min": 9,    # 1分钟
                "5min": 0,    # 5分钟
                "15min": 1,   # 15分钟
                "30min": 2,   # 30分钟
                "1h": 3,      # 1小时
                "1day": 5,    # 日K
                "1week": 6,   # 周K
                "1month": 7,  # 月K
            }

            kline_type = interval_map.get(interval)
            if kline_type is None:
                return []

            # 解析符号
            if symbol.upper().startswith("SH") or symbol.startswith("6"):
                market = 1
                code = symbol.replace("SH", "").replace("sh", "")
            else:
                market = 0
                code = symbol.replace("SZ", "").replace("sz", "")

            loop = get_event_loop()

            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_bars(kline_type, market, code, start=0, count=limit)
            )

            bars = []
            for item in reversed(data or []):
                try:
                    dt = datetime.strptime(item["datetime"], "%Y-%m-%d %H:%M:%S")

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
                except Exception:
                    continue

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
        return await self.get_stock_bars(symbol, interval, start_time, end_time, limit)

    async def get_stock_ticks(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Tick]:
        """获取股票逐笔成交"""
        # modtdx支持获取逐笔成交
        if not self.is_connected or not self.api:
            return []

        try:
            # 解析符号
            if symbol.upper().startswith("SH") or symbol.startswith("6"):
                market = 1
                code = symbol.replace("SH", "").replace("sh", "")
            else:
                market = 0
                code = symbol.replace("SZ", "").replace("sz", "")

            loop = get_event_loop()

            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_history_transaction_data(market, code, start=0, count=limit)
            )

            ticks = []
            for item in data or []:
                try:
                    dt = datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")

                    if start_time and dt < start_time:
                        continue
                    if end_time and dt > end_time:
                        continue

                    direction = "B" if item["buyorsell"] == 1 else "S"

                    ticks.append(Tick(
                        symbol=symbol,
                        ts=dt,
                        price=float(item["price"]),
                        volume=float(item["vol"]),
                        amount=float(item["amount"]),
                        direction=direction
                    ))
                except Exception:
                    continue

            return ticks

        except Exception as e:
            logger.error(f"{self.name}: get_stock_ticks error - {e}")
            return []
