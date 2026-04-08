# -*- coding: utf-8 -*-
"""
组合管理器
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
from .calculator import Position, PortfolioSnapshot, PortfolioCalculator
from .risk import RiskAnalyzer


class PortfolioManager:
    """投资组合管理器"""

    def __init__(self, portfolio_id: int = 0, name: str = "Default"):
        self.portfolio_id = portfolio_id
        self.name = name
        self._positions: Dict[str, Position] = {}
        self._cash: float = 0
        self._initial_capital: float = 0
        self._nav_history: List[float] = []
        self._returns_history: List[float] = []
        self._created_at: datetime = datetime.now()

    def initialize(self, capital: float):
        """初始化组合资金"""
        self._cash = capital
        self._initial_capital = capital
        self._nav_history = [capital]

    @property
    def total_assets(self) -> float:
        return self._cash + sum(p.market_value for p in self._positions.values())

    @property
    def position_value(self) -> float:
        return sum(p.market_value for p in self._positions.values())

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> List[Position]:
        return list(self._positions.values())

    @property
    def position_count(self) -> int:
        return len([p for p in self._positions.values() if p.quantity > 0])

    def buy(self, symbol: str, quantity: float, price: float, name: str = "") -> bool:
        """买入"""
        cost = quantity * price
        if cost > self._cash:
            logger.warning(f"Insufficient cash: need {cost}, have {self._cash}")
            return False

        self._cash -= cost

        if symbol in self._positions:
            pos = self._positions[symbol]
            total_cost = pos.cost_value + cost
            total_qty = pos.quantity + quantity
            pos.cost_price = total_cost / total_qty if total_qty > 0 else 0
            pos.quantity = total_qty
            pos.current_price = price
        else:
            self._positions[symbol] = Position(
                symbol=symbol, name=name,
                quantity=quantity, cost_price=price, current_price=price,
            )
        return True

    def sell(self, symbol: str, quantity: float, price: float) -> bool:
        """卖出"""
        if symbol not in self._positions:
            return False

        pos = self._positions[symbol]
        if quantity > pos.quantity:
            logger.warning(f"Insufficient position: need {quantity}, have {pos.quantity}")
            return False

        self._cash += quantity * price
        pos.quantity -= quantity
        pos.current_price = price

        if pos.quantity <= 0:
            pos.quantity = 0
        return True

    def update_prices(self, prices: Dict[str, float]):
        """更新持仓价格"""
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].current_price = price

    def get_snapshot(self) -> PortfolioSnapshot:
        """获取组合快照"""
        snapshot = PortfolioSnapshot(
            total_assets=self.total_assets,
            cash=self._cash,
            positions=self.positions,
        )

        if len(self._nav_history) >= 2:
            prev_nav = self._nav_history[-1]
            snapshot.daily_return = PortfolioCalculator.calculate_daily_return(
                self.total_assets, prev_nav
            )

        if self._initial_capital > 0:
            snapshot.cumulative_return = PortfolioCalculator.calculate_cumulative_return(
                self._initial_capital, self.total_assets
            )

        return snapshot

    def record_nav(self):
        """记录当日净值"""
        nav = self.total_assets
        if self._nav_history:
            prev = self._nav_history[-1]
            ret = PortfolioCalculator.calculate_daily_return(nav, prev)
            self._returns_history.append(ret)
        self._nav_history.append(nav)

    def get_performance(self) -> Dict[str, Any]:
        """获取绩效分析"""
        snapshot = self.get_snapshot()

        weights = PortfolioCalculator.calculate_position_weights(self.positions)
        result = {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "total_assets": round(snapshot.total_assets, 2),
            "cash": round(snapshot.cash, 2),
            "position_value": round(snapshot.position_value, 2),
            "position_count": snapshot.position_count,
            "cumulative_return": round(snapshot.cumulative_return, 4),
            "daily_return": round(snapshot.daily_return, 4),
            "positions": [p.to_dict() for p in self.positions],
            "weights": {k: round(v, 4) for k, v in weights.items()},
        }

        if self._returns_history:
            risk = RiskAnalyzer.full_analysis(
                self._returns_history,
                self._nav_history,
            )
            result["risk_metrics"] = {k: round(v, 4) for k, v in risk.items()}

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "cash": self._cash,
            "initial_capital": self._initial_capital,
            "total_assets": self.total_assets,
            "position_count": self.position_count,
            "created_at": self._created_at.isoformat(),
        }
