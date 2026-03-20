# -*- coding: utf-8 -*-
"""
期货数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class FuturesExchange(str, Enum):
    """期货交易所"""
    SHFE = "SHFE"       # 上海期货交易所
    DCE = "DCE"         # 大连商品交易所
    CZCE = "CZCE"       # 郑州商品交易所
    CFFEX = "CFFEX"     # 中国金融期货交易所
    GFEX = "GFEX"       # 广州期货交易所
    INE = "INE"         # 上海国际能源交易中心


class FuturesType(str, Enum):
    """期货类型"""
    COMMODITY = "commodity"  # 商品期货
    FINANCIAL = "financial"  # 金融期货
    INDEX = "index"          # 股指期货
    BOND = "bond"            # 国债期货


class ContractType(str, Enum):
    """合约类型"""
    MAIN = "main"       # 主力合约
    SECOND = "second"   # 次主力合约
    ALL = "all"         # 所有合约


class FuturesQuote(BaseModel):
    """期货实时行情"""
    symbol: str = Field(..., description="合约代码")
    name: Optional[str] = Field(None, description="合约名称")
    exchange: FuturesExchange = Field(..., description="交易所")
    ts: datetime = Field(..., description="时间戳")

    # 价格
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    close: Optional[float] = Field(None, description="收盘价/当前价")
    pre_close: Optional[float] = Field(None, description="昨结算价")
    pre_settlement: Optional[float] = Field(None, description="昨结算价")
    settlement: Optional[float] = Field(None, description="今结算价")

    # 成交量额
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    open_interest: Optional[float] = Field(None, description="持仓量")
    pre_open_interest: Optional[float] = Field(None, description="昨持仓")

    # 涨跌
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅%")

    # 买卖盘
    bid_price1: Optional[float] = Field(None, description="买一价")
    bid_volume1: Optional[float] = Field(None, description="买一量")
    ask_price1: Optional[float] = Field(None, description="卖一价")
    ask_volume1: Optional[float] = Field(None, description="卖一量")


class FuturesBar(BaseModel):
    """期货K线数据"""
    symbol: str = Field(..., description="合约代码")
    exchange: FuturesExchange = Field(..., description="交易所")
    interval: str = Field(..., description="周期: 1min, 5min, 15min, 30min, 60min, 1day, 1week, 1month")
    ts: datetime = Field(..., description="时间戳")

    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    open_interest: Optional[float] = Field(None, description="持仓量")
    settlement: Optional[float] = Field(None, description="结算价")


class FuturesTick(BaseModel):
    """期货逐笔成交"""
    symbol: str = Field(..., description="合约代码")
    exchange: FuturesExchange = Field(..., description="交易所")
    ts: datetime = Field(..., description="时间戳")

    price: float = Field(..., description="成交价")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    direction: str = Field(..., description="方向: B-买入, S-卖出, N-未知")
    open_interest: Optional[float] = Field(None, description="持仓量")


class FuturesContract(BaseModel):
    """期货合约信息"""
    symbol: str = Field(..., description="合约代码")
    name: str = Field(..., description="合约名称")
    exchange: FuturesExchange = Field(..., description="交易所")
    product: str = Field(..., description="产品代码: AU, AG, CU等")
    contract_type: ContractType = Field(..., description="合约类型")

    # 交易信息
    trade_unit: Optional[float] = Field(None, description="交易单位")
    price_tick: Optional[float] = Field(None, description="最小变动价位")
    margin_rate: Optional[float] = Field(None, description="保证金比例%")

    # 合约信息
    list_date: Optional[datetime] = Field(None, description="上市日")
    last_trade_date: Optional[datetime] = Field(None, description="最后交易日")
    delivery_date: Optional[datetime] = Field(None, description="交割日")

    # 状态
    is_trading: bool = Field(True, description="是否交易中")


class FuturesPositionDetail(BaseModel):
    """期货持仓明细"""
    symbol: str = Field(..., description="合约代码")
    exchange: FuturesExchange = Field(..., description="交易所")
    date: datetime = Field(..., description="日期")

    # 多头持仓
    long_volume: Optional[float] = Field(None, description="多头持仓量")
    long_change: Optional[float] = Field(None, description="多头持仓变化")

    # 空头持仓
    short_volume: Optional[float] = Field(None, description="空头持仓量")
    short_change: Optional[float] = Field(None, description="空头持仓变化")

    # 会员排名
    rank: Optional[int] = Field(None, description="排名")
    member_name: Optional[str] = Field(None, description="会员名称")
