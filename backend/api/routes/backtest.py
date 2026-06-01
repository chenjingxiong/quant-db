# -*- coding: utf-8 -*-
"""
策略回测API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter()


class BacktestRequest(BaseModel):
    """回测请求"""
    symbol: str = Field(..., description="证券代码")
    strategy: str = Field("DualMA", description="策略名称: DualMA/RSI")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    initial_capital: float = Field(1000000, description="初始资金")
    commission_rate: float = Field(0.0003, description="手续费率")
    slippage: float = Field(0.0, description="滑点")
    strategy_params: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    interval: str = Field("1day", description="K线周期")
    limit: int = Field(500, ge=1, le=5000, description="K线数量")


class BacktestResponse(BaseModel):
    """回测响应"""
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_loss_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int


@router.get("/strategies")
async def list_strategies():
    """获取可用策略列表"""
    return {
        "strategies": [
            {"name": "DualMA", "description": "双均线策略", "params": ["fast", "slow"]},
            {"name": "RSI", "description": "RSI超买超卖策略", "params": ["period", "oversold", "overbought"]},
        ]
    }


@router.post("/run", response_model=Dict[str, Any])
async def run_backtest(request: BacktestRequest):
    """运行回测"""
    try:
        from ...services.backtest import BacktestEngine, Bar
        from ...services.backtest.strategy import DualMAStrategy, RSIStrategy

        # 获取数据
        bars_data = _get_mock_bars(request.symbol, request.limit)
        if not bars_data:
            raise HTTPException(status_code=404, detail=f"No data for {request.symbol}")

        bars = [Bar.from_dict(b) for b in bars_data]

        # 创建策略
        params = request.strategy_params or {}
        if request.strategy == "DualMA":
            strategy = DualMAStrategy(
                fast=params.get("fast", 5),
                slow=params.get("slow", 20),
            )
        elif request.strategy == "RSI":
            strategy = RSIStrategy(
                period=params.get("period", 14),
                oversold=params.get("oversold", 30),
                overbought=params.get("overbought", 70),
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")

        # 运行回测
        engine = BacktestEngine(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage=request.slippage,
        )
        result = engine.run(strategy, bars)

        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_mock_bars(symbol: str, count: int) -> List[Dict]:
    """生成模拟K线数据"""
    import random
    from datetime import datetime, timedelta

    random.seed(hash(symbol) % 2**31)

    bars = []
    price = 10.0 + random.uniform(0, 50)
    base_date = datetime(2024, 1, 2)

    for i in range(count):
        # Skip weekends for realistic trading days
        current_date = base_date + timedelta(days=i)
        while current_date.weekday() >= 5:  # Saturday=5, Sunday=6
            current_date += timedelta(days=1)
            base_date = current_date

        change = random.gauss(0, 0.02)
        open_p = price
        close_p = price * (1 + change)
        high_p = max(open_p, close_p) * (1 + abs(random.gauss(0, 0.005)))
        low_p = min(open_p, close_p) * (1 - abs(random.gauss(0, 0.005)))
        vol = random.randint(100000, 10000000)

        bars.append({
            "symbol": symbol,
            "ts": current_date.strftime("%Y-%m-%d"),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": vol,
            "amount": round(close_p * vol, 2),
        })
        price = close_p

    return bars
