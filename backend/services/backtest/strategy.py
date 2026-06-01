# -*- coding: utf-8 -*-
"""
策略基类
"""
from typing import List, Optional
from .models import Bar, Order, OrderSide, OrderType, OrderStatus


class BaseStrategy:
    """策略基类"""

    name: str = "BaseStrategy"

    def __init__(self):
        self._bars: List[Bar] = []
        self._cash: float = 0
        self._positions: dict = {}
        self._orders: List[Order] = []

    def on_init(self, cash: float):
        """策略初始化"""
        self._cash = cash
        self._bars = []
        self._positions = {}
        self._orders = []

    def on_bar(self, bar: Bar):
        """K线事件处理 - 子类必须实现"""
        pass

    def on_trade(self, trade):
        """成交回调"""
        pass

    # 工具方法
    def buy(self, symbol: str, quantity: float, price: Optional[float] = None):
        """买入"""
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            price=price or self._current_price(symbol),
            order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
        )
        self._orders.append(order)

    def sell(self, symbol: str, quantity: float, price: Optional[float] = None):
        """卖出"""
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            price=price or self._current_price(symbol),
            order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
        )
        self._orders.append(order)

    def sell_all(self, symbol: str):
        """清仓"""
        pos = self._positions.get(symbol)
        if pos and pos.quantity > 0:
            self.sell(symbol, pos.quantity)

    def _current_price(self, symbol: str) -> float:
        """获取当前价格"""
        if self._bars:
            return self._bars[-1].close
        return 0

    @property
    def bars(self) -> List[Bar]:
        return self._bars

    @property
    def last_bar(self) -> Optional[Bar]:
        return self._bars[-1] if self._bars else None

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> dict:
        return self._positions

    @property
    def pending_orders(self) -> List[Order]:
        return [o for o in self._orders if o.status == OrderStatus.PENDING]

    def close_prices(self, period: int = 0) -> List[float]:
        """获取收盘价序列"""
        if period > 0:
            return [b.close for b in self._bars[-period:]]
        return [b.close for b in self._bars]

    def sma(self, period: int) -> Optional[float]:
        """简单移动平均"""
        prices = self.close_prices(period)
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period


class DualMAStrategy(BaseStrategy):
    """双均线策略"""

    name = "DualMA"

    def __init__(self, fast: int = 5, slow: int = 20):
        super().__init__()
        self.fast = fast
        self.slow = slow

    def on_bar(self, bar: Bar):
        self._bars.append(bar)

        if len(self._bars) < self.slow:
            return

        fast_ma = self.sma(self.fast)
        slow_ma = self.sma(self.slow)

        if fast_ma is None or slow_ma is None:
            return

        symbol = bar.symbol
        has_position = symbol in self._positions and self._positions[symbol].quantity > 0

        # 金叉买入
        if fast_ma > slow_ma and not has_position:
            qty = int(self._cash / bar.close / 100) * 100  # 整手买入
            if qty > 0:
                self.buy(symbol, qty)

        # 死叉卖出
        elif fast_ma < slow_ma and has_position:
            self.sell_all(symbol)


class RSIStrategy(BaseStrategy):
    """RSI超买超卖策略"""

    name = "RSI"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, bar: Bar):
        self._bars.append(bar)

        if len(self._bars) < self.period + 1:
            return

        rsi = self._calc_rsi()
        if rsi is None:
            return

        symbol = bar.symbol
        has_position = symbol in self._positions and self._positions[symbol].quantity > 0

        if rsi < self.oversold and not has_position:
            qty = int(self._cash / bar.close / 100) * 100
            if qty > 0:
                self.buy(symbol, qty)
        elif rsi > self.overbought and has_position:
            self.sell_all(symbol)

    def _calc_rsi(self) -> Optional[float]:
        closes = self.close_prices()
        if len(closes) < self.period + 1:
            return None

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-self.period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-self.period:]]

        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)
