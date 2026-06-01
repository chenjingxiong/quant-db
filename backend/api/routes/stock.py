# -*- coding: utf-8 -*-
"""
股票数据API路由
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from loguru import logger

from ...storage import TDEngineClient
from ...adapters import PytdxAdapter
from ...models.stock import StockQuote, StockBar

router = APIRouter()


class StockQuoteResponse(BaseModel):
    """股票行情响应"""
    symbol: str
    ts: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    pre_close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None


class StockBarResponse(BaseModel):
    """股票K线响应"""
    symbol: str
    interval: str
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float


class StockListResponse(BaseModel):
    """股票列表响应"""
    symbols: List[dict]
    total: int


@router.get("/quotes", response_model=List[StockQuoteResponse])
async def get_stock_quotes(
    symbols: str = Query(..., description="股票代码列表，逗号分隔，如 000001,600000"),
):
    """
    获取股票实时行情

    支持从缓存或数据源获取最新行情数据
    """
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            # 如果数据库未连接，尝试直接从数据源获取
            adapter = PytdxAdapter()
            try:
                await adapter.connect()
                symbol_list = symbols.split(",")
                quotes = await adapter.get_stock_quotes(symbol_list)
            finally:
                await adapter.disconnect()

            result = []
            for q in quotes:
                result.append(StockQuoteResponse(
                    symbol=q.symbol,
                    ts=q.ts.isoformat(),
                    open=q.open,
                    high=q.high,
                    low=q.low,
                    close=q.close,
                    pre_close=q.pre_close,
                    volume=q.volume,
                    amount=q.amount,
                    change=q.change,
                    change_percent=q.change_percent,
                ))
            return result

        # 从数据库查询
        symbol_list = symbols.split(",")
        result = []

        for symbol in symbol_list:
            quote = await client.query_stock_quote_latest(symbol)
            if quote:
                result.append(StockQuoteResponse(
                    symbol=symbol,
                    ts=quote.get("ts", ""),
                    open=quote.get("open"),
                    high=quote.get("high"),
                    low=quote.get("low"),
                    close=quote.get("close"),
                    pre_close=quote.get("pre_close"),
                    volume=quote.get("volume"),
                    amount=quote.get("amount"),
                    change=quote.get("change"),
                    change_percent=quote.get("change_percent"),
                ))

        return result

    except Exception as e:
        logger.error(f"Get stock quotes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bars", response_model=List[StockBarResponse])
async def get_stock_bars(
    symbol: str = Query(..., description="股票代码"),
    interval: str = Query("1day", description="K线周期"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=10000, description="数量限制"),
):
    """
    获取股票K线数据

    支持多种周期：1min, 5min, 15min, 30min, 60min, 1day, 1week, 1month
    """
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            raise HTTPException(status_code=503, detail="Database not available")

        # 解析时间
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        # 查询数据
        bars = await client.query_stock_bars(
            symbol=symbol,
            interval=interval,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
        )

        result = []
        for bar in bars:
            result.append(StockBarResponse(
                symbol=symbol,
                interval=interval,
                ts=bar.get("ts", ""),
                open=bar.get("open", 0),
                high=bar.get("high", 0),
                low=bar.get("low", 0),
                close=bar.get("close", 0),
                volume=bar.get("volume", 0),
                amount=bar.get("amount", 0),
            ))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get stock bars error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=StockListResponse)
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场: SH/SZ"),
    limit: int = Query(5000, ge=1, le=50000, description="数量限制"),
):
    """
    获取股票列表

    返回指定市场的所有股票代码和名称
    """
    try:
        adapter = PytdxAdapter()
        try:
            await adapter.connect()
            stocks = await adapter.get_all_stock_list()
        finally:
            await adapter.disconnect()

        # 过滤市场
        if market:
            stocks = [s for s in stocks if s.get("market") == market.upper()]

        # 限制数量
        stocks = stocks[:limit]

        return StockListResponse(
            symbols=stocks,
            total=len(stocks),
        )

    except Exception as e:
        logger.error(f"Get stock list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/quote")
async def get_stock_quote(symbol: str):
    """获取单个股票行情"""
    try:
        quotes = await get_stock_quotes(symbols=symbol)
        if quotes:
            return quotes[0]
        # 无数据时返回空行情
        return StockQuoteResponse(
            symbol=symbol,
            ts="",
        )
    except Exception as e:
        logger.error(f"Get stock quote error: {e}")
        return StockQuoteResponse(symbol=symbol, ts="")


@router.get("/{symbol}/detail")
async def get_stock_detail(symbol: str):
    """获取股票详细信息"""
    try:
        # 这里可以返回股票的基本信息、财务数据等
        # 暂时返回基础信息
        return {
            "symbol": symbol,
            "name": "",
            "market": "SH" if symbol.startswith("6") else "SZ",
            "industry": "",
            "description": "Stock detail",
        }
    except Exception as e:
        logger.error(f"Get stock detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
