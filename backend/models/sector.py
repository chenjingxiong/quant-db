# -*- coding: utf-8 -*-
"""
板块数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class SectorType(str, Enum):
    """板块类型"""
    INDUSTRY = "industry"  # 行业板块
    CONCEPT = "concept"    # 概念板块
    REGION = "region"      # 地域板块


class SectorQuote(BaseModel):
    """板块实时行情"""
    name: str = Field(..., description="板块名称")
    sector_type: SectorType = Field(..., description="板块类型")
    ts: datetime = Field(..., description="时间戳")

    # 指数
    index: Optional[float] = Field(None, description="板块指数")
    pre_index: Optional[float] = Field(None, description="昨收指数")

    # 涨跌
    change: Optional[float] = Field(None, description="涨跌点")
    change_percent: Optional[float] = Field(None, description="涨跌幅%")

    # 成交量额
    amount: Optional[float] = Field(None, description="成交额")

    # 成分股统计
    stock_count: Optional[int] = Field(None, description="成分股数量")
    up_count: Optional[int] = Field(None, description="上涨家数")
    down_count: Optional[int] = Field(None, description="下跌家数")
    limit_up_count: Optional[int] = Field(None, description="涨停家数")
    limit_down_count: Optional[int] = Field(None, description="跌停家数")

    # 领涨股票
    leader_stock: Optional[str] = Field(None, description="领涨股票")
    leader_change: Optional[float] = Field(None, description="领涨涨幅%")

    # 成分股列表
    stocks: Optional[List[str]] = Field(None, description="成分股代码列表")
