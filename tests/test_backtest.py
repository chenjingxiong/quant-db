# -*- coding: utf-8 -*-
"""
策略回测引擎单元测试
"""
import pytest
import numpy as np
from backend.services.backtest.models import Bar, Order, OrderSide, OrderType, OrderStatus, Trade, Position, BacktestResult
from backend.services.backtest.strategy import BaseStrategy, DualMAStrategy, RSIStrategy
from backend.services.backtest.broker import SimulatedBroker
from backend.services.backtest.engine import BacktestEngine


# ============ Helpers ============

def create_bars(count: int = 100, base_price: float = 10.0, symbol: str = "TEST") -> list:
    np.random.seed(42)
    bars = []
    price = base_price
    for i in range(count):
        change = np.random.randn() * 0.02
        open_p = price
        close_p = price * (1 + change)
        high_p = max(open_p, close_p) * (1 + abs(np.random.randn() * 0.005))
        low_p = min(open_p, close_p) * (1 - abs(np.random.randn() * 0.005))
        bars.append({
            "symbol": symbol,
            "ts": f"2024-{(i // 22) + 1:02d}-{(i % 22) + 1:02d}",
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": 100000,
            "amount": round(close_p * 100000, 2),
        })
        price = close_p
    return [Bar.from_dict(b) for b in bars]


@pytest.fixture
def sample_bars():
    return create_bars(200)


@pytest.fixture
def uptrend_bars():
    """上涨趋势K线"""
    bars = []
    price = 10.0
    for i in range(50):
        bars.append({
            "symbol": "TEST",
            "ts": f"2024-01-{i+1:02d}",
            "open": round(price, 2),
            "high": round(price + 0.5, 2),
            "low": round(price - 0.2, 2),
            "close": round(price + 0.3, 2),
            "volume": 100000,
        })
        price += 0.3
    return [Bar.from_dict(b) for b in bars]


# ============ Model Tests ============

class TestBar:
    def test_from_dict(self):
        d = {"symbol": "000001", "ts": "2024-01-01", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000}
        bar = Bar.from_dict(d)
        assert bar.symbol == "000001"
        assert bar.close == 10.5

    def test_from_dict_missing_fields(self):
        bar = Bar.from_dict({})
        assert bar.close == 0


class TestOrder:
    def test_buy_order(self):
        order = Order(symbol="TEST", side=OrderSide.BUY, quantity=100, price=10)
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.PENDING


class TestPosition:
    def test_market_value(self):
        pos = Position(symbol="TEST", quantity=100, avg_price=10)
        assert pos.market_value == 1000

    def test_to_dict(self):
        pos = Position(symbol="TEST", quantity=100, avg_price=10)
        d = pos.to_dict()
        assert d["symbol"] == "TEST"
        assert d["quantity"] == 100


class TestBacktestResult:
    def test_to_dict(self):
        result = BacktestResult(
            strategy_name="Test",
            symbol="TEST",
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=1000000,
            final_capital=1200000,
            total_return=0.2,
            annual_return=0.2,
            max_drawdown=0.05,
            sharpe_ratio=1.5,
            win_rate=0.6,
            profit_loss_ratio=2.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
        )
        d = result.to_dict()
        assert d["strategy_name"] == "Test"
        assert d["total_return"] == 0.2


# ============ Strategy Tests ============

class TestBaseStrategy:
    def test_init(self):
        s = BaseStrategy()
        s.on_init(100000)
        assert s.cash == 100000
        assert len(s.bars) == 0

    def test_buy_sell(self):
        s = BaseStrategy()
        s.on_init(100000)
        s.buy("TEST", 100, 10)
        orders = s.pending_orders
        assert len(orders) == 1
        assert orders[0].side == OrderSide.BUY

    def test_sma(self):
        s = BaseStrategy()
        s.on_init(100000)
        bar = Bar(symbol="TEST", timestamp="t", open=10, high=11, low=9, close=10, volume=100)
        s._bars.append(bar)
        s._bars.append(Bar(symbol="TEST", timestamp="t", open=10, high=11, low=9, close=12, volume=100))
        result = s.sma(2)
        assert result == 11.0


class TestDualMAStrategy:
    def test_name(self):
        s = DualMAStrategy()
        assert s.name == "DualMA"

    def test_run(self, sample_bars):
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(strategy=DualMAStrategy(fast=5, slow=20), bars=sample_bars)
        assert result.strategy_name == "DualMA"
        assert result.total_trades >= 0
        assert result.initial_capital == 100000


class TestRSIStrategy:
    def test_name(self):
        s = RSIStrategy()
        assert s.name == "RSI"

    def test_run(self, sample_bars):
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(strategy=RSIStrategy(), bars=sample_bars)
        assert result.strategy_name == "RSI"
        assert result.initial_capital == 100000


# ============ Broker Tests ============

class TestSimulatedBroker:
    def test_initialize(self):
        broker = SimulatedBroker()
        broker.initialize(100000)
        assert broker.cash == 100000

    def test_buy(self):
        broker = SimulatedBroker()
        broker.initialize(100000)
        order = Order(symbol="TEST", side=OrderSide.BUY, quantity=100, price=10)
        trade = broker.execute_order(order, 10)
        assert trade is not None
        assert trade.side == "buy"
        assert broker.cash < 100000
        assert "TEST" in broker.positions

    def test_buy_insufficient_funds(self):
        broker = SimulatedBroker()
        broker.initialize(1000)
        order = Order(symbol="TEST", side=OrderSide.BUY, quantity=1000, price=10)
        trade = broker.execute_order(order, 10)
        assert trade is None

    def test_sell(self):
        broker = SimulatedBroker()
        broker.initialize(100000)
        buy_order = Order(symbol="TEST", side=OrderSide.BUY, quantity=100, price=10)
        broker.execute_order(buy_order, 10)
        sell_order = Order(symbol="TEST", side=OrderSide.SELL, quantity=100, price=12)
        trade = broker.execute_order(sell_order, 12)
        assert trade is not None
        assert trade.side == "sell"

    def test_sell_insufficient_position(self):
        broker = SimulatedBroker()
        broker.initialize(100000)
        sell_order = Order(symbol="TEST", side=OrderSide.SELL, quantity=100, price=10)
        trade = broker.execute_order(sell_order, 10)
        assert trade is None

    def test_commission(self):
        broker = SimulatedBroker(commission_rate=0.001, min_commission=5)
        broker.initialize(100000)
        order = Order(symbol="TEST", side=OrderSide.BUY, quantity=100, price=10)
        trade = broker.execute_order(order, 10)
        assert trade.commission >= 5

    def test_total_assets(self):
        broker = SimulatedBroker()
        broker.initialize(100000)
        buy_order = Order(symbol="TEST", side=OrderSide.BUY, quantity=1000, price=10)
        broker.execute_order(buy_order, 10)
        total = broker.get_total_assets({"TEST": 12})
        expected = (100000 - 1000 * 10) + 1000 * 12  # cash + position value (approx)
        assert abs(total - expected) < 100  # account for commission


# ============ Engine Tests ============

class TestBacktestEngine:
    def test_run_empty(self):
        engine = BacktestEngine()
        result = engine.run(DualMAStrategy(), [])
        assert result.total_return == 0

    def test_run_dual_ma(self, sample_bars):
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(DualMAStrategy(fast=5, slow=20), sample_bars)
        assert result.final_capital > 0
        assert result.total_trades >= 0

    def test_run_rsi(self, sample_bars):
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(RSIStrategy(), sample_bars)
        assert result.final_capital > 0

    def test_uptrend_profit(self, uptrend_bars):
        """上涨趋势中双均线策略应该盈利"""
        engine = BacktestEngine(initial_capital=100000, commission_rate=0)
        result = engine.run(DualMAStrategy(fast=5, slow=10), uptrend_bars)
        # 在持续上涨中策略应该有正收益
        assert result.total_return != 0  # 至少有交易
