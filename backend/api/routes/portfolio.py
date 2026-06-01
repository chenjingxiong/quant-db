# -*- coding: utf-8 -*-
"""
投资组合管理API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter()


# ============ Models ============

class PortfolioCreate(BaseModel):
    name: str = Field(..., description="组合名称")
    description: Optional[str] = None
    initial_capital: float = Field(1000000, description="初始资金")


class PortfolioResponse(BaseModel):
    id: int
    name: str
    total_assets: float
    cash: float
    position_count: int


class PositionAdd(BaseModel):
    symbol: str
    name: Optional[str] = ""
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)


class PositionSell(BaseModel):
    symbol: str
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)


class PerformanceResponse(BaseModel):
    portfolio_id: int
    name: str
    total_assets: float
    cash: float
    position_value: float
    position_count: int
    cumulative_return: float
    daily_return: float
    positions: List[Dict[str, Any]]
    weights: Dict[str, float]
    risk_metrics: Optional[Dict[str, Any]] = None


# 内存存储（实际应使用PostgreSQL）
_portfolios: Dict[int, Any] = {}
_next_id = 1


@router.post("", response_model=PortfolioResponse)
async def create_portfolio(portfolio: PortfolioCreate):
    """创建投资组合"""
    global _next_id
    try:
        from ...services.portfolio import PortfolioManager
        pm = PortfolioManager(portfolio_id=_next_id, name=portfolio.name)
        pm.initialize(portfolio.initial_capital)
        _portfolios[_next_id] = pm
        _next_id += 1

        d = pm.to_dict()
        return PortfolioResponse(
            id=d["portfolio_id"], name=d["name"],
            total_assets=d["total_assets"], cash=d["cash"],
            position_count=d["position_count"],
        )
    except Exception as e:
        logger.error(f"Create portfolio error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[PortfolioResponse])
async def list_portfolios():
    """获取组合列表"""
    result = []
    for pm in _portfolios.values():
        d = pm.to_dict()
        result.append(PortfolioResponse(
            id=d["portfolio_id"], name=d["name"],
            total_assets=d["total_assets"], cash=d["cash"],
            position_count=d["position_count"],
        ))
    return result


@router.get("/{portfolio_id}", response_model=PerformanceResponse)
async def get_portfolio_detail(portfolio_id: int):
    """获取组合详情"""
    if portfolio_id not in _portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    pm = _portfolios[portfolio_id]
    perf = pm.get_performance()
    return PerformanceResponse(**perf)


@router.post("/{portfolio_id}/positions", response_model=Dict[str, Any])
async def add_position(portfolio_id: int, position: PositionAdd):
    """添加持仓"""
    if portfolio_id not in _portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    pm = _portfolios[portfolio_id]
    success = pm.buy(position.symbol, position.quantity, position.price, position.name)
    if not success:
        raise HTTPException(status_code=400, detail="Buy failed - insufficient cash")
    return {"success": True, "total_assets": pm.total_assets}


@router.delete("/{portfolio_id}/positions/{symbol}")
async def sell_position(portfolio_id: int, symbol: str, sell: PositionSell):
    """卖出持仓"""
    if portfolio_id not in _portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    pm = _portfolios[portfolio_id]
    success = pm.sell(sell.symbol, sell.quantity, sell.price)
    if not success:
        raise HTTPException(status_code=400, detail="Sell failed")
    return {"success": True, "total_assets": pm.total_assets}


@router.get("/{portfolio_id}/performance", response_model=PerformanceResponse)
async def get_portfolio_performance(portfolio_id: int):
    """获取组合绩效分析"""
    if portfolio_id not in _portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    pm = _portfolios[portfolio_id]
    perf = pm.get_performance()
    return PerformanceResponse(**perf)
