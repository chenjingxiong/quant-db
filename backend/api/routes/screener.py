# -*- coding: utf-8 -*-
"""
智能选股和自选股API路由
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter()


# ============ 选股策略模型 ============

class ScreenerConfig(BaseModel):
    """选股配置"""
    basic: Optional[Dict[str, Any]] = Field(None, description="基础筛选条件")
    technical: Optional[Dict[str, Any]] = Field(None, description="技术指标条件")
    financial: Optional[Dict[str, Any]] = Field(None, description="财务指标条件")
    logic: str = Field("and", description="条件组合逻辑: and/or")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: str = Field("desc", description="排序方向")
    limit: int = Field(50, ge=1, le=500, description="返回数量")


class ScreenerStrategyCreate(BaseModel):
    """创建选股策略"""
    name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    config: ScreenerConfig


class ScreenerStrategyResponse(BaseModel):
    """选股策略响应"""
    id: int
    name: str
    description: Optional[str]
    config: Dict[str, Any]


class ScreenerResultResponse(BaseModel):
    """选股结果响应"""
    total: int
    conditions: List[str]
    stocks: List[Dict[str, Any]]


# ============ 自选股模型 ============

class WatchlistAdd(BaseModel):
    """添加自选股"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    notes: Optional[str] = Field(None, description="备注")


class WatchlistItem(BaseModel):
    """自选股项目"""
    id: int
    symbol: str
    name: Optional[str]
    notes: Optional[str]
    added_at: str


# ============ 选股API ============

@router.post("/run", response_model=ScreenerResultResponse)
async def run_screener(config: ScreenerConfig):
    """
    执行选股

    根据配置的条件进行筛选
    """
    try:
        from ...services.screener import ScreenerEngine

        engine = ScreenerEngine()
        engine.set_conditions_from_config(config.dict())

        # 模拟股票数据（实际应从数据库获取）
        stocks = _get_mock_stock_data()

        result = engine.screen(
            stocks=stocks,
            logic=config.logic,
            sort_by=config.sort_by,
            sort_order=config.sort_order,
            limit=config.limit,
        )

        return ScreenerResultResponse(
            total=len(result),
            conditions=engine.get_condition_descriptions(),
            stocks=result,
        )
    except Exception as e:
        logger.error(f"Run screener error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies", response_model=List[ScreenerStrategyResponse])
async def list_screener_strategies():
    """获取选股策略列表"""
    # 实际应从PostgreSQL查询
    return []


@router.post("/strategies", response_model=ScreenerStrategyResponse)
async def create_screener_strategy(strategy: ScreenerStrategyCreate):
    """创建选股策略"""
    try:
        return ScreenerStrategyResponse(
            id=1,
            name=strategy.name,
            description=strategy.description,
            config=strategy.config.dict(),
        )
    except Exception as e:
        logger.error(f"Create strategy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 自选股API ============

@router.get("/watchlist", response_model=List[WatchlistItem])
async def get_watchlist():
    """获取自选股列表"""
    try:
        from ...db.postgres_client import get_postgres_client
        pg = await get_postgres_client()
        rows = await pg.fetch_all(
            "SELECT id, symbol, name, notes, added_at::text FROM watchlist ORDER BY added_at DESC"
        )
        return [WatchlistItem(**dict(r)) for r in rows]
    except Exception as e:
        logger.warning(f"Get watchlist error: {e}")
        return []


@router.post("/watchlist", response_model=WatchlistItem)
async def add_to_watchlist(item: WatchlistAdd):
    """添加自选股"""
    try:
        from ...db.postgres_client import get_postgres_client
        pg = await get_postgres_client()
        row = await pg.fetch_one(
            "INSERT INTO watchlist (symbol, name, notes) VALUES ($1, $2, $3) "
            "ON CONFLICT (symbol) DO NOTHING "
            "RETURNING id, symbol, name, notes, added_at::text",
            item.symbol, item.name, item.notes,
        )
        if row:
            return WatchlistItem(**dict(row))
        raise HTTPException(status_code=409, detail="Already in watchlist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add to watchlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """删除自选股"""
    try:
        from ...db.postgres_client import get_postgres_client
        pg = await get_postgres_client()
        await pg.execute("DELETE FROM watchlist WHERE symbol = $1", symbol)
        return {"success": True, "message": f"Removed {symbol} from watchlist"}
    except Exception as e:
        logger.error(f"Remove from watchlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_mock_stock_data() -> List[Dict[str, Any]]:
    """获取模拟股票数据"""
    import random
    random.seed(42)
    stocks = []
    symbols = [
        "000001", "000002", "000063", "000333", "000338",
        "000425", "000538", "000568", "000625", "000651",
        "000725", "000768", "000776", "000858", "000895",
        "600000", "600009", "600016", "600019", "600028",
        "600030", "600036", "600048", "600050", "600104",
        "600115", "600150", "600276", "600309", "600340",
    ]
    names = [
        "平安银行", "万科A", "中兴通讯", "美的集团", "潍柴动力",
        "徐工机械", "云南白药", "泸州老窖", "长安汽车", "格力电器",
        "京东方A", "中航飞机", "广发证券", "五粮液", "双汇发展",
        "浦发银行", "上海机场", "民生银行", "宝钢股份", "中国石化",
        "中信证券", "招商银行", "保利地产", "中国联通", "上汽集团",
        "东方航空", "中国船舶", "恒瑞医药", "万华化学", "华夏幸福",
    ]

    for i, (sym, name) in enumerate(zip(symbols, names)):
        pe = random.uniform(5, 80)
        pb = random.uniform(0.5, 10)
        roe = random.uniform(-5, 40)
        price = random.uniform(5, 100)
        market_cap = price * random.uniform(1e9, 5e10)
        change_percent = random.uniform(-10, 10)
        volume = random.uniform(1e6, 1e9)
        turnover_rate = random.uniform(0.5, 15)
        amplitude = random.uniform(1, 10)
        rsi6 = random.uniform(10, 90)
        ma5 = price * random.uniform(0.95, 1.05)
        ma10 = price * random.uniform(0.90, 1.10)
        ma20 = price * random.uniform(0.85, 1.15)
        macd_dif = random.uniform(-1, 1)
        volume_ratio = random.uniform(0.3, 3.0)

        stocks.append({
            "symbol": sym,
            "name": name,
            "market": "SH" if sym.startswith("6") else "SZ",
            "price": round(price, 2),
            "pe": round(pe, 2),
            "pb": round(pb, 2),
            "roe": round(roe, 2),
            "market_cap": round(market_cap, 0),
            "change_percent": round(change_percent, 2),
            "volume": round(volume, 0),
            "turnover_rate": round(turnover_rate, 2),
            "amplitude": round(amplitude, 2),
            "rsi6": round(rsi6, 2),
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "macd_dif": round(macd_dif, 4),
            "volume_ratio": round(volume_ratio, 2),
        })
    return stocks
