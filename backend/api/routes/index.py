# -*- coding: utf-8 -*-
"""
指数数据API路由
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from loguru import logger

import re
from ...storage import TDEngineClient

router = APIRouter()


def _validate_identifier(name: str) -> str:
    """Validate SQL identifier (table/column name) to prevent injection."""
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise HTTPException(status_code=400, detail=f"Invalid identifier: {name}")
    return name


@router.get("/quotes")
async def get_index_quotes(
    symbols: str = Query(..., description="指数代码列表，逗号分隔"),
):
    """获取指数实时行情"""
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            # 从数据源获取
            from ...adapters import PytdxAdapter
            adapter = PytdxAdapter()
            await adapter.connect()
            symbol_list = symbols.split(",")
            quotes = await adapter.get_index_quotes(symbol_list)
            await adapter.disconnect()

            return {
                "quotes": [
                    {
                        "symbol": q.symbol,
                        "ts": q.ts.isoformat(),
                        "close": q.close,
                        "change": q.change,
                        "change_percent": q.change_percent,
                    }
                    for q in quotes
                ]
            }

        # 从数据库查询
        symbol_list = symbols.split(",")
        result = []

        for symbol in symbol_list:
            table_name = f"index_quotes_{_validate_identifier(symbol)}"
            sql = f"SELECT * FROM {table_name} ORDER BY ts DESC LIMIT 1"
            data = await client.query(sql)

            if data:
                result.append(data[0])

        return {"quotes": result}

    except Exception as e:
        logger.error(f"Get index quotes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bars")
async def get_index_bars(
    symbol: str = Query(..., description="指数代码"),
    interval: str = Query("1day", description="K线周期"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=10000, description="数量限制"),
):
    """获取指数K线数据"""
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            raise HTTPException(status_code=503, detail="Database not available")

        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        table_name = f"index_bars_{_validate_identifier(symbol)}"
        validated_interval = _validate_identifier(interval)
        sql = f"SELECT * FROM {table_name} WHERE `interval` = '{validated_interval}'"

        if start_dt:
            sql += f" AND ts >= '{start_dt.strftime('%Y-%m-%d %H:%M:%S')}'"
        if end_dt:
            sql += f" AND ts <= '{end_dt.strftime('%Y-%m-%d %H:%M:%S')}'"

        sql += f" ORDER BY ts DESC LIMIT {int(limit)}"

        data = await client.query(sql)

        return {
            "symbol": symbol,
            "interval": interval,
            "data": data,
            "total": len(data),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get index bars error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_index_list():
    """获取指数列表"""
    # 常见指数
    indices = [
        {"code": "000001", "name": "上证指数", "market": "SH"},
        {"code": "399001", "name": "深证成指", "market": "SZ"},
        {"code": "399006", "name": "创业板指", "market": "SZ"},
        {"code": "000300", "name": "沪深300", "market": "SH"},
        {"code": "000905", "name": "中证500", "market": "SH"},
        {"code": "000852", "name": "中证1000", "market": "SH"},
    ]
    return {"indices": indices}
