# -*- coding: utf-8 -*-
"""
数据源适配器基类
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from loguru import logger


class Quote(BaseModel):
    """通用行情数据"""
    symbol: str
    ts: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None

    # 扩展数据
    extra: Dict[str, Any] = {}


class Bar(BaseModel):
    """通用K线数据"""
    symbol: str
    interval: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float

    # 扩展数据
    extra: Dict[str, Any] = {}


class Tick(BaseModel):
    """通用逐笔成交"""
    symbol: str
    ts: datetime
    price: float
    volume: float
    amount: float
    direction: str  # B=买入, S=卖出, N=未知

    # 扩展数据
    extra: Dict[str, Any] = {}


class BaseAdapter(ABC):
    """
    数据源适配器基类

    所有数据源适配器都需要实现这个接口
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.is_connected = False
        self.name = self.__class__.__name__

    @abstractmethod
    async def connect(self) -> bool:
        """
        连接数据源

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def get_stock_quotes(self, symbols: List[str]) -> List[Quote]:
        """
        获取股票实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            List[Quote]: 股票行情列表
        """
        pass

    @abstractmethod
    async def get_futures_quotes(self, symbols: List[str]) -> List[Quote]:
        """
        获取期货实时行情

        Args:
            symbols: 合约代码列表

        Returns:
            List[Quote]: 期货行情列表
        """
        pass

    @abstractmethod
    async def get_stock_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """
        获取股票K线数据

        Args:
            symbol: 股票代码
            interval: K线周期 (1min, 5min, 15min, 30min, 60min, 1day, 1week, 1month)
            start_time: 开始时间
            end_time: 结束时间
            limit: 数量限制

        Returns:
            List[Bar]: K线数据列表
        """
        pass

    @abstractmethod
    async def get_futures_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """
        获取期货K线数据

        Args:
            symbol: 合约代码
            interval: K线周期
            start_time: 开始时间
            end_time: 结束时间
            limit: 数量限制

        Returns:
            List[Bar]: K线数据列表
        """
        pass

    @abstractmethod
    async def get_stock_ticks(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Tick]:
        """
        获取股票逐笔成交

        Args:
            symbol: 股票代码
            start_time: 开始时间
            end_time: 结束时间
            limit: 数量限制

        Returns:
            List[Tick]: 逐笔成交列表
        """
        pass

    async def get_index_quotes(self, symbols: List[str]) -> List[Quote]:
        """
        获取指数实时行情（默认实现，子类可覆盖）

        Args:
            symbols: 指数代码列表

        Returns:
            List[Quote]: 指数行情列表
        """
        logger.warning(f"{self.name}: get_index_quotes not implemented")
        return []

    async def get_sector_quotes(self, sectors: List[str]) -> List[Quote]:
        """
        获取板块实时行情（默认实现，子类可覆盖）

        Args:
            sectors: 板块名称列表

        Returns:
            List[Quote]: 板块行情列表
        """
        logger.warning(f"{self.name}: get_sector_quotes not implemented")
        return []

    async def get_all_stock_list(self) -> List[Dict[str, Any]]:
        """
        获取所有股票列表（默认实现，子类可覆盖）

        Returns:
            List[Dict]: 股票信息列表
        """
        logger.warning(f"{self.name}: get_all_stock_list not implemented")
        return []

    async def get_all_futures_list(self) -> List[Dict[str, Any]]:
        """
        获取所有期货合约列表（默认实现，子类可覆盖）

        Returns:
            List[Dict]: 合约信息列表
        """
        logger.warning(f"{self.name}: get_all_futures_list not implemented")
        return []

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 是否健康
        """
        try:
            if not self.is_connected:
                return await self.connect()

            # 尝试获取一些数据来验证连接
            quotes = await self.get_stock_quotes(["000001"])
            return len(quotes) > 0 or True  # 即使没有数据也算连接正常

        except Exception as e:
            logger.error(f"{self.name}: health check failed - {e}")
            return False

    def __repr__(self) -> str:
        return f"{self.name}(connected={self.is_connected})"
