# -*- coding: utf-8 -*-
"""
模拟交易券商
"""
from typing import Dict, List, Optional
from .models import Order, OrderSide, OrderStatus, Trade, Position as BTPosition


class SimulatedBroker:
    """模拟券商"""

    def __init__(
        self,
        commission_rate: float = 0.0003,
        slippage: float = 0.0,
        min_commission: float = 5.0,
    ):
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.min_commission = min_commission
        self._cash: float = 0
        self._positions: Dict[str, BTPosition] = {}
        self._trades: List[Trade] = []

    def initialize(self, cash: float):
        self._cash = cash
        self._positions.clear()
        self._trades.clear()

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> Dict[str, BTPosition]:
        return self._positions

    @property
    def trades(self) -> List[Trade]:
        return self._trades

    def execute_order(self, order: Order, market_price: float) -> Optional[Trade]:
        """执行订单"""
        if order.status != OrderStatus.PENDING:
            return None

        # 计算成交价（含滑点）
        if order.side == OrderSide.BUY:
            fill_price = market_price * (1 + self.slippage)
        else:
            fill_price = market_price * (1 - self.slippage)

        # 计算金额和手续费
        amount = fill_price * order.quantity
        commission = max(amount * self.commission_rate, self.min_commission)

        if order.side == OrderSide.BUY:
            total_cost = amount + commission
            if total_cost > self._cash:
                order.status = OrderStatus.CANCELLED
                return None

            self._cash -= total_cost

            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                total_qty = pos.quantity + order.quantity
                pos.avg_price = (pos.avg_price * pos.quantity + fill_price * order.quantity) / total_qty
                pos.quantity = total_qty
            else:
                self._positions[order.symbol] = BTPosition(
                    symbol=order.symbol, quantity=order.quantity, avg_price=fill_price,
                )

        else:  # SELL
            if order.symbol not in self._positions or self._positions[order.symbol].quantity < order.quantity:
                order.status = OrderStatus.CANCELLED
                return None

            pos = self._positions[order.symbol]
            pnl = (fill_price - pos.avg_price) * order.quantity - commission
            self._cash += amount - commission
            pos.quantity -= order.quantity

            if pos.quantity <= 0:
                pos.quantity = 0

        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = commission

        trade = Trade(
            symbol=order.symbol,
            side=order.side.value,
            price=fill_price,
            quantity=order.quantity,
            amount=amount,
            commission=commission,
            timestamp=order.timestamp,
            profit_loss=pnl if order.side == OrderSide.SELL else 0,
        )
        self._trades.append(trade)
        return trade

    def get_total_assets(self, current_prices: Dict[str, float]) -> float:
        """计算总资产"""
        position_value = sum(
            self._positions[s].quantity * current_prices.get(s, 0)
            for s in self._positions
        )
        return self._cash + position_value
