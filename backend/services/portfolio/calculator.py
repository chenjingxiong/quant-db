# -*- coding: utf-8 -*-
"""
组合收益计算器
"""
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Position:
    """持仓"""
    symbol: str
    name: str = ""
    quantity: float = 0
    cost_price: float = 0
    current_price: float = 0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_value(self) -> float:
        return self.quantity * self.cost_price

    @property
    def profit_loss(self) -> float:
        return self.market_value - self.cost_value

    @property
    def profit_loss_percent(self) -> float:
        if self.cost_value == 0:
            return 0
        return (self.profit_loss / self.cost_value) * 100

    @property
    def weight(self) -> float:
        """需在总市值上下文中计算"""
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_value": self.cost_value,
            "profit_loss": round(self.profit_loss, 2),
            "profit_loss_percent": round(self.profit_loss_percent, 2),
        }


@dataclass
class PortfolioSnapshot:
    """组合快照"""
    total_assets: float = 0
    cash: float = 0
    positions: List[Position] = field(default_factory=list)
    daily_return: float = 0
    cumulative_return: float = 0

    @property
    def position_count(self) -> int:
        return len([p for p in self.positions if p.quantity > 0])

    @property
    def position_value(self) -> float:
        return sum(p.market_value for p in self.positions)


class PortfolioCalculator:
    """组合收益计算器"""

    @staticmethod
    def calculate_daily_return(nav_today: float, nav_yesterday: float) -> float:
        """计算日收益率"""
        if nav_yesterday == 0:
            return 0
        return (nav_today - nav_yesterday) / nav_yesterday

    @staticmethod
    def calculate_cumulative_return(initial_nav: float, current_nav: float) -> float:
        """计算累计收益率"""
        if initial_nav == 0:
            return 0
        return (current_nav - initial_nav) / initial_nav

    @staticmethod
    def calculate_annual_return(cumulative_return: float, days: int) -> float:
        """计算年化收益率"""
        if days <= 0:
            return 0
        return (1 + cumulative_return) ** (365 / days) - 1

    @staticmethod
    def calculate_position_weights(positions: List[Position]) -> Dict[str, float]:
        """计算持仓权重"""
        total = sum(p.market_value for p in positions)
        if total == 0:
            return {p.symbol: 0 for p in positions}
        return {p.symbol: p.market_value / total for p in positions}

    @staticmethod
    def calculate_portfolio_return(
        positions: List[Position],
        returns: Dict[str, float],
    ) -> float:
        """根据持仓权重和个股收益率计算组合收益率"""
        weights = PortfolioCalculator.calculate_position_weights(positions)
        total_return = 0
        for symbol, weight in weights.items():
            stock_return = returns.get(symbol, 0)
            total_return += weight * stock_return
        return total_return

    @staticmethod
    def calculate_nav_series(
        initial_capital: float,
        daily_returns: List[float],
    ) -> List[float]:
        """计算净值序列"""
        nav_series = [initial_capital]
        for ret in daily_returns:
            nav_series.append(nav_series[-1] * (1 + ret))
        return nav_series
