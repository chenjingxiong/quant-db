# -*- coding: utf-8 -*-
"""
技术指标API路由
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter()


class IndicatorListResponse(BaseModel):
    """指标列表响应"""
    indicators: List[Dict[str, str]]
    total: int


class IndicatorCalculateRequest(BaseModel):
    """指标计算请求"""
    symbol: str = Field(..., description="证券代码")
    interval: str = Field("1day", description="K线周期")
    indicators: Optional[List[str]] = Field(None, description="指标列表，None表示全部")
    params: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="指标参数覆盖")
    limit: int = Field(100, ge=1, le=1000, description="K线数量")


class IndicatorCalculateResponse(BaseModel):
    """指标计算响应"""
    symbol: str
    interval: str
    count: int
    indicators: Dict[str, Any]


@router.get("/list", response_model=IndicatorListResponse)
async def list_indicators():
    """获取支持的指标列表"""
    from ...services.indicators import IndicatorCalculator
    indicators = IndicatorCalculator.list_indicators()
    return IndicatorListResponse(indicators=indicators, total=len(indicators))


@router.get("/{symbol}/calculate", response_model=IndicatorCalculateResponse)
async def calculate_indicators(
    symbol: str,
    interval: str = Query("1day", description="K线周期"),
    indicator_names: Optional[str] = Query(None, alias="indicators", description="指标名称，逗号分隔"),
    limit: int = Query(100, ge=1, le=1000, description="K线数量"),
):
    """
    计算指定证券的技术指标

    从数据库获取K线数据后计算技术指标
    """
    try:
        from ...api.app import get_td_client
        from ...services.indicators import IndicatorCalculator
        from ...services.indicators.base import BarData

        client = get_td_client()
        if not client:
            raise HTTPException(status_code=503, detail="Database not available")

        # 获取K线数据
        bars = await client.query_stock_bars(symbol=symbol, interval=interval, limit=limit)
        if not bars:
            raise HTTPException(status_code=404, detail=f"No bar data found for {symbol}")

        bar_data = BarData.from_dicts(bars)

        # 计算指标
        calc = IndicatorCalculator()
        ind_list = indicator_names.split(",") if indicator_names else None
        results = calc.calculate(bar_data, ind_list)

        # 序列化结果
        indicators_data = {}
        for name, result in results.items():
            indicators_data[name] = {
                "params": result.params,
                "latest": result.latest(),
                "values": result.values,
            }

        return IndicatorCalculateResponse(
            symbol=symbol,
            interval=interval,
            count=len(bars),
            indicators=indicators_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Calculate indicators error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=Dict[str, IndicatorCalculateResponse])
async def batch_calculate_indicators(request: IndicatorCalculateRequest):
    """批量计算指标（POST方式）"""
    try:
        from ...api.app import get_td_client
        from ...services.indicators import IndicatorCalculator
        from ...services.indicators.base import BarData

        client = get_td_client()
        if not client:
            raise HTTPException(status_code=503, detail="Database not available")

        bars = await client.query_stock_bars(
            symbol=request.symbol, interval=request.interval, limit=request.limit
        )
        if not bars:
            raise HTTPException(status_code=404, detail=f"No data for {request.symbol}")

        bar_data = BarData.from_dicts(bars)

        calc = IndicatorCalculator()
        if request.params:
            for name, params in request.params.items():
                from ...services.indicators.calculator import INDICATOR_REGISTRY
                cls = INDICATOR_REGISTRY.get(name.upper())
                if cls:
                    calc.register(name, cls(**params))

        results = calc.calculate(bar_data, request.indicators)

        indicators_data = {}
        for name, result in results.items():
            indicators_data[name] = {
                "params": result.params,
                "latest": result.latest(),
                "values": result.values,
            }

        return {
            request.symbol: IndicatorCalculateResponse(
                symbol=request.symbol,
                interval=request.interval,
                count=len(bars),
                indicators=indicators_data,
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch calculate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
