# -*- coding: utf-8 -*-
"""
指数数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class IndexType(str, Enum):
    """指数类型"""
    BROAD = "broad"        # 宽基指数
    SECTOR = "sector"      # 行业指数
    CONCEPT = "concept"    # 概念指数
    STRATEGY = "strategy"  # 策略指数


class IndexQuote(BaseModel):
    """指数实时行情"""
    symbol: str = Field(..., description="指数代码")
    name: Optional[str] = Field(None, description="指数名称")
    index_type: IndexType = Field(..., description="指数类型")
    ts: datetime = Field(..., description="时间戳")

    # 价格
    open: Optional[float] = Field(None, description="开盘点")
    high: Optional[float] = Field(None, description="最高点")
    low: Optional[float] = Field(None, description="最低点")
    close: Optional[float] = Field(None, description="收盘点/当前点")
    pre_close: Optional[float] = Field(None, description="昨收点")

    # 涨跌
    change: Optional[float] = Field(None, description="涨跌点")
    change_percent: Optional[float] = Field(None, description="涨跌幅%")

    # 成交量额（成分股合计）
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")

    # 成分股统计
    up_count: Optional[int] = Field(None, description="上涨家数")
    down_count: Optional[int] = Field(None, description="下跌家数")
    unchanged_count: Optional[int] = Field(None, description="平盘家数")


class IndexBar(BaseModel):
    """指数K线数据"""
    symbol: str = Field(..., description="指数代码")
    index_type: IndexType = Field(..., description="指数类型")
    interval: str = Field(..., description="周期: 1min, 5min, 15min, 30min, 60min, 1day, 1week, 1month")
    ts: datetime = Field(..., description="时间戳")

    open: float = Field(..., description="开盘点")
    high: float = Field(..., description="最高点")
    low: float = Field(..., description="最低点")
    close: float = Field(..., description="收盘点")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
