# -*- coding: utf-8 -*-
"""
期货数据API路由
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from loguru import logger

from ...storage import TDEngineClient

router = APIRouter()


class FuturesQuoteResponse(BaseModel):
    """期货行情响应"""
    symbol: str
    ts: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    open_interest: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None


@router.get("/quotes", response_model=List[FuturesQuoteResponse])
async def get_futures_quotes(
    symbols: str = Query(..., description="合约代码列表，逗号分隔"),
):
    """获取期货实时行情"""
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            # 从数据源获取
            from ...adapters import PytdxAdapter
            adapter = PytdxAdapter()
            await adapter.connect()
            symbol_list = symbols.split(",")
            quotes = await adapter.get_futures_quotes(symbol_list)
            await adapter.disconnect()

            result = []
            for q in quotes:
                result.append(FuturesQuoteResponse(
                    symbol=q.symbol,
                    ts=q.ts.isoformat(),
                    open=q.open,
                    high=q.high,
                    low=q.low,
                    close=q.close,
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
            data = await client.query_futures_quote_latest(symbol)

            if data:
                row = data
                result.append(FuturesQuoteResponse(
                    symbol=symbol,
                    ts=row.get("ts", ""),
                    open=row.get("open"),
                    high=row.get("high"),
                    low=row.get("low"),
                    close=row.get("close"),
                    volume=row.get("volume"),
                    amount=row.get("amount"),
                    open_interest=row.get("open_interest"),
                    change=row.get("change"),
                    change_percent=row.get("change_percent"),
                ))

        return result

    except Exception as e:
        logger.error(f"Get futures quotes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bars")
async def get_futures_bars(
    symbol: str = Query(..., description="合约代码"),
    interval: str = Query("1day", description="K线周期"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=10000, description="数量限制"),
):
    """获取期货K线数据"""
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            raise HTTPException(status_code=503, detail="Database not available")

        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        data = await client.query_futures_bars(
            symbol=symbol,
            interval=interval,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
        )

        return {
            "symbol": symbol,
            "interval": interval,
            "data": data,
            "total": len(data),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get futures bars error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_futures_list(
    exchange: Optional[str] = Query(None, description="交易所"),
):
    """获取期货合约列表"""
    try:
        from ...adapters import PytdxAdapter
        adapter = PytdxAdapter()
        await adapter.connect()

        contracts = await adapter.get_all_futures_list()

        await adapter.disconnect()

        if exchange:
            contracts = [c for c in contracts if c.get("exchange") == exchange.upper()]

        return {
            "contracts": contracts,
            "total": len(contracts),
        }

    except Exception as e:
        logger.error(f"Get futures list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exchanges")
async def get_exchanges():
    """获取支持的交易所列表"""
    exchanges = [
        {"code": "SHFE", "name": "上海期货交易所"},
        {"code": "DCE", "name": "大连商品交易所"},
        {"code": "CZCE", "name": "郑州商品交易所"},
        {"code": "CFFEX", "name": "中国金融期货交易所"},
        {"code": "GFEX", "name": "广州期货交易所"},
        {"code": "INE", "name": "上海国际能源交易中心"},
    ]
    return {"exchanges": exchanges}
