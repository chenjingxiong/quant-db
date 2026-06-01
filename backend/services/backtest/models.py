# -*- coding: utf-8 -*-
"""
回测数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Bar:
    """K线数据"""
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0

    @classmethod
    def from_dict(cls, d: Dict) -> "Bar":
        return cls(
            symbol=d.get("symbol", ""),
            timestamp=str(d.get("ts", "")),
            open=float(d.get("open", 0)),
            high=float(d.get("high", 0)),
            low=float(d.get("low", 0)),
            close=float(d.get("close", 0)),
            volume=float(d.get("volume", 0)),
            amount=float(d.get("amount", 0)),
        )


@dataclass
class Order:
    """订单"""
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    timestamp: str = ""
    filled_price: float = 0
    filled_quantity: float = 0
    commission: float = 0


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    side: str
    price: float
    quantity: float
    amount: float
    commission: float
    timestamp: str
    profit_loss: float = 0


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float = 0
    avg_price: float = 0

    @property
    def market_value(self) -> float:
        return self.quantity * self.avg_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_price": self.avg_price,
            "market_value": self.market_value,
        }


@dataclass
class BacktestResult:
    """回测结果"""
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
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_capital": round(self.final_capital, 2),
            "total_return": round(self.total_return, 4),
            "annual_return": round(self.annual_return, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_loss_ratio": round(self.profit_loss_ratio, 4),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "trades": [
                {"symbol": t.symbol, "side": t.side, "price": t.price,
                 "quantity": t.quantity, "timestamp": t.timestamp, "pnl": t.profit_loss}
                for t in self.trades
            ],
            "equity_curve": [round(v, 2) for v in self.equity_curve[-100:]],
        }
