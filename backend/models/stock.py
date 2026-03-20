# -*- coding: utf-8 -*-
"""
股票数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class MarketType(str, Enum):
    """市场类型"""
    SH = "SH"  # 上海证券交易所
    SZ = "SZ"  # 深圳证券交易所
    BJ = "BJ"  # 北京证券交易所


class StockType(str, Enum):
    """股票类型"""
    STOCK = "stock"      # 股票
    INDEX = "index"      # 指数
    ETF = "etf"          # ETF
    LOF = "lof"          # LOF
    FUND = "fund"        # 基金


class ListBoardType(str, Enum):
    """板块类型"""
    MAIN = "main"        # 主板
    SME = "sme"          # 中小板
    STARTUP = "startup"  # 创业板
    STAR = "star"        # 科创板
    BSE = "bse"          # 北交所


class StockQuote(BaseModel):
    """股票实时行情"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    market: MarketType = Field(..., description="市场")
    ts: datetime = Field(..., description="时间戳")

    # 价格
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    close: Optional[float] = Field(None, description="收盘价/当前价")
    pre_close: Optional[float] = Field(None, description="昨收价")

    # 成交量额
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")

    # 涨跌
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅%")

    # 买卖盘
    bid_price1: Optional[float] = Field(None, description="买一价")
    bid_volume1: Optional[float] = Field(None, description="买一量")
    bid_price2: Optional[float] = Field(None, description="买二价")
    bid_volume2: Optional[float] = Field(None, description="买二量")
    bid_price3: Optional[float] = Field(None, description="买三价")
    bid_volume3: Optional[float] = Field(None, description="买三量")
    bid_price4: Optional[float] = Field(None, description="买四价")
    bid_volume4: Optional[float] = Field(None, description="买四量")
    bid_price5: Optional[float] = Field(None, description="买五价")
    bid_volume5: Optional[float] = Field(None, description="买五量")

    ask_price1: Optional[float] = Field(None, description="卖一价")
    ask_volume1: Optional[float] = Field(None, description="卖一量")
    ask_price2: Optional[float] = Field(None, description="卖二价")
    ask_volume2: Optional[float] = Field(None, description="卖二量")
    ask_price3: Optional[float] = Field(None, description="卖三价")
    ask_volume3: Optional[float] = Field(None, description="卖三量")
    ask_price4: Optional[float] = Field(None, description="卖四价")
    ask_volume4: Optional[float] = Field(None, description="卖四量")
    ask_price5: Optional[float] = Field(None, description="卖五价")
    ask_volume5: Optional[float] = Field(None, description="卖五量")

    # 其他
    turnover: Optional[float] = Field(None, description="换手率%")
    pe: Optional[float] = Field(None, description="市盈率")
    market_cap: Optional[float] = Field(None, description="总市值")


class StockBar(BaseModel):
    """股票K线数据"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场")
    interval: str = Field(..., description="周期: 1min, 5min, 15min, 30min, 60min, 1day, 1week, 1month")
    ts: datetime = Field(..., description="时间戳")

    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")

    # 可选字段
    turnover: Optional[float] = Field(None, description="换手率%")


class StockTick(BaseModel):
    """股票逐笔成交"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场")
    ts: datetime = Field(..., description="时间戳")

    price: float = Field(..., description="成交价")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    direction: str = Field(..., description="方向: B-买入, S-卖出, N-未知")


class StockInfo(BaseModel):
    """股票基本信息"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: MarketType = Field(..., description="市场")
    stock_type: StockType = Field(..., description="股票类型")
    list_board: ListBoardType = Field(..., description="上市板块")
    list_date: Optional[datetime] = Field(None, description="上市日期")

    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")
    concept: Optional[str] = Field(None, description="概念板块")

    total_share: Optional[float] = Field(None, description="总股本")
    float_share: Optional[float] = Field(None, description="流通股本")


class StockFinancial(BaseModel):
    """股票财务数据"""
    symbol: str = Field(..., description="股票代码")
    report_date: datetime = Field(..., description="报告期")

    # 利润表
    revenue: Optional[float] = Field(None, description="营业收入")
    net_profit: Optional[float] = Field(None, description="净利润")

    # 资产负债表
    total_assets: Optional[float] = Field(None, description="总资产")
    total_liability: Optional[float] = Field(None, description="总负债")
    equity: Optional[float] = Field(None, description="股东权益")

    # 现金流量表
    operating_cash_flow: Optional[float] = Field(None, description="经营现金流")

    # 财务指标
    roe: Optional[float] = Field(None, description="净资产收益率%")
    roa: Optional[float] = Field(None, description="总资产收益率%")
    debt_ratio: Optional[float] = Field(None, description="资产负债率%")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")


class StockDividend(BaseModel):
    """股票分红送配"""
    symbol: str = Field(..., description="股票代码")
    ex_date: datetime = Field(..., description="除权除息日")
    dividend_per_share: Optional[float] = Field(None, description="每股分红")
    bonus_share_ratio: Optional[float] = Field(None, description="每股送股比例")
    rights_issue_ratio: Optional[float] = Field(None, description="每股配股比例")


class StockMoneyFlow(BaseModel):
    """股票资金流向"""
    symbol: str = Field(..., description="股票代码")
    date: datetime = Field(..., description="日期")

    # 主力资金
    main_net_inflow: Optional[float] = Field(None, description="主力净流入")
    super_large_net_inflow: Optional[float] = Field(None, description="超大单净流入")
    large_net_inflow: Optional[float] = Field(None, description="大单净流入")
    medium_net_inflow: Optional[float] = Field(None, description="中单净流入")
    small_net_inflow: Optional[float] = Field(None, description="小单净流入")
