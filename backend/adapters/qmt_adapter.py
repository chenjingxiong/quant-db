# -*- coding: utf-8 -*-
"""
QMT (迅投) 数据源适配器

QMT是迅投提供的量化交易平台，支持实盘交易和行情数据
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import os

from .base import BaseAdapter, Quote, Bar, Tick
from ..utils.async_helper import get_event_loop


class QmtAdapter(BaseAdapter):
    """
    QMT 数据源适配器

    注意: QMT需要安装迅投客户端，并获取相关SDK
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 配置
        self.qmt_path = self.config.get("qmt_path", "/data/qmt")
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 18080)

        # QMT API客户端
        self.api = None

        # 检查QMT是否可用
        self._check_qmt_available()

    def _check_qmt_available(self):
        """检查QMT是否可用"""
        try:
            # 尝试导入QMT SDK
            # 这里假设QMT提供Python SDK
            from xtquant import xtdata
            self.xtdata = xtdata
            self.QMT_AVAILABLE = True
            logger.info(f"{self.name}: QMT SDK available")
        except ImportError:
            self.QMT_AVAILABLE = False
            logger.warning(f"{self.name}: QMT SDK not installed")

        # 检查QMT路径
        if not os.path.exists(self.qmt_path):
            logger.warning(f"{self.name}: QMT path not found: {self.qmt_path}")

    async def connect(self) -> bool:
        """连接QMT"""
        if not self.QMT_AVAILABLE:
            logger.warning(f"{self.name}: QMT not available")
            return False

        try:
            # QMT连接
            # 连接交易服务器
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.xtdata.connect(path=self.qmt_path, session_id=0)
            )

            if result == 0:
                self.is_connected = True
                logger.info(f"{self.name}: connected to QMT")
                return True
            else:
                logger.error(f"{self.name}: QMT connect failed with code {result}")
                return False

        except Exception as e:
            logger.error(f"{self.name}: connect error - {e}")
            return False

    async def disconnect(self):
        """断开QMT连接"""
        if self.is_connected and self.QMT_AVAILABLE:
            try:
                await asyncio.get_running_loop().run_in_executor(None, lambda: self.xtdata.disconnect())
            except Exception as e:
                logger.error(f"{self.name}: disconnect error - {e}")
            finally:
                self.is_connected = False

    async def get_stock_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取股票实时行情"""
        if not self.is_connected or not self.QMT_AVAILABLE:
            return []

        try:
            loop = get_event_loop()

            # QMT获取全市场股票报价
            all_quotes = await loop.run_in_executor(
                None,
                lambda: self.xtdata.get_full_tick(symbols)
            )

            quotes = []
            now = datetime.now()

            for symbol, data in all_quotes.items():
                try:
                    quotes.append(Quote(
                        symbol=symbol,
                        ts=now,
                        open=float(data.get("lastOpen", 0)) or None,
                        high=float(data.get("lastHigh", 0)) or None,
                        low=float(data.get("lastLow", 0)) or None,
                        close=float(data.get("lastPrice", 0)) or None,
                        volume=float(data.get("volume", 0)) or None,
                        amount=float(data.get("amount", 0)) or None,
                        pre_close=float(data.get("lastClose", 0)) or None,
                        extra={
                            "name": data.get("name", ""),
                            "bid1": float(data.get("bidPrice1", 0)) or None,
                            "bid_vol1": float(data.get("bidVol1", 0)) or None,
                            "ask1": float(data.get("askPrice1", 0)) or None,
                            "ask_vol1": float(data.get("askVol1", 0)) or None,
                        }
                    ))
                except Exception:
                    continue

            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_stock_quotes error - {e}")
            return []

    async def get_futures_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取期货实时行情"""
        # QMT的期货行情获取方式与股票类似
        return await self.get_stock_quotes(symbols)

    async def get_stock_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[ datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取股票K线数据"""
        if not self.is_connected or not self.QMT_AVAILABLE:
            return []

        try:
            # K线周期映射
            period_map = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "30min": "30m",
                "1h": "1h",
                "1day": "1d",
                "1week": "1w",
                "1month": "1M",
            }

            period = period_map.get(interval)
            if not period:
                logger.warning(f"{self.name}: unsupported interval {interval}")
                return []

            loop = get_event_loop()

            # 获取K线数据
            data = await loop.run_in_executor(
                None,
                lambda: self.xtdata.get_market_data(
                    field_list=["open", "high", "low", "close", "volume", "amount"],
                    stock_list=[symbol],
                    period=period,
                    start_time="" if not start_time else start_time.strftime("%Y%m%d %H:%M:%S"),
                    end_time="" if not end_time else end_time.strftime("%Y%m%d %H:%M:%S"),
                    count=limit,
                    dividend_type="none"
                )
            )

            bars = []
            # QMT返回的数据结构需要解析
            if symbol in data:
                for i, ts in enumerate(data[symbol].get("time", [])):
                    try:
                        dt = datetime.fromtimestamp(ts / 1000)  # QMT返回毫秒时间戳

                        bars.append(Bar(
                            symbol=symbol,
                            interval=interval,
                            ts=dt,
                            open=float(data[symbol]["open"][i]),
                            high=float(data[symbol]["high"][i]),
                            low=float(data[symbol]["low"][i]),
                            close=float(data[symbol]["close"][i]),
                            volume=float(data[symbol]["volume"][i]),
                            amount=float(data[symbol]["amount"][i]),
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
        if not self.is_connected or not self.QMT_AVAILABLE:
            return []

        try:
            loop = get_event_loop()

            # QMT获取逐笔成交
            data = await loop.run_in_executor(
                None,
                lambda: self.xtdata.get_full_tick([symbol])
            )

            ticks = []
            # QMT的tick数据结构需要解析
            # 这里简化处理，实际使用时需要根据QMT API调整

            return ticks

        except Exception as e:
            logger.error(f"{self.name}: get_stock_ticks error - {e}")
            return []

    async def get_all_stock_list(self) -> List[Dict[str, Any]]:
        """获取所有股票列表"""
        if not self.is_connected or not self.QMT_AVAILABLE:
            return []

        try:
            loop = get_event_loop()

            # 获取所有股票列表
            stocks = await loop.run_in_executor(
                None,
                lambda: self.xtdata.get_stock_list_in_sector("沪深A股")
            )

            result = []
            for stock in stocks:
                result.append({
                    "symbol": stock,
                    "code": stock,
                    "name": "",
                    "market": "SH" if stock.startswith("6") else "SZ"
                })

            return result

        except Exception as e:
            logger.error(f"{self.name}: get_all_stock_list error - {e}")
            return []
