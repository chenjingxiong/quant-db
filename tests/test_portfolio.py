# -*- coding: utf-8 -*-
"""
投资组合管理单元测试
"""
import pytest
import numpy as np
from backend.services.portfolio.manager import PortfolioManager
from backend.services.portfolio.calculator import (
    Position, PortfolioCalculator, PortfolioSnapshot,
)
from backend.services.portfolio.risk import RiskAnalyzer


# ============ Position Tests ============

class TestPosition:
    def test_market_value(self):
        pos = Position(symbol="000001", quantity=1000, cost_price=10, current_price=12)
        assert pos.market_value == 12000

    def test_cost_value(self):
        pos = Position(symbol="000001", quantity=1000, cost_price=10)
        assert pos.cost_value == 10000

    def test_profit_loss(self):
        pos = Position(symbol="000001", quantity=1000, cost_price=10, current_price=12)
        assert pos.profit_loss == 2000

    def test_profit_loss_percent(self):
        pos = Position(symbol="000001", quantity=1000, cost_price=10, current_price=12)
        assert pos.profit_loss_percent == 20.0

    def test_zero_cost(self):
        pos = Position(symbol="000001", quantity=0, cost_price=0)
        assert pos.profit_loss_percent == 0

    def test_to_dict(self):
        pos = Position(symbol="000001", name="平安银行", quantity=1000, cost_price=10, current_price=12)
        d = pos.to_dict()
        assert d["symbol"] == "000001"
        assert d["market_value"] == 12000
        assert d["profit_loss"] == 2000


# ============ PortfolioCalculator Tests ============

class TestPortfolioCalculator:
    def test_daily_return(self):
        ret = PortfolioCalculator.calculate_daily_return(105, 100)
        assert abs(ret - 0.05) < 1e-6

    def test_daily_return_zero(self):
        ret = PortfolioCalculator.calculate_daily_return(100, 0)
        assert ret == 0

    def test_cumulative_return(self):
        # calculate_cumulative_return(initial_nav=100, current_nav=120) = (120-100)/100 = 0.2
        ret = PortfolioCalculator.calculate_cumulative_return(100, 120)
        assert abs(ret - 0.2) < 1e-6

    def test_cumulative_return_loss(self):
        ret = PortfolioCalculator.calculate_cumulative_return(100, 80)
        assert abs(ret - (-0.2)) < 1e-6

    def test_annual_return(self):
        cum_ret = 0.2
        annual = PortfolioCalculator.calculate_annual_return(cum_ret, 365)
        assert abs(annual - 0.2) < 1e-6

    def test_position_weights(self):
        positions = [
            Position("A", quantity=100, current_price=10),
            Position("B", quantity=200, current_price=5),
        ]
        weights = PortfolioCalculator.calculate_position_weights(positions)
        assert abs(weights["A"] - 0.5) < 1e-6
        assert abs(weights["B"] - 0.5) < 1e-6

    def test_nav_series(self):
        nav = PortfolioCalculator.calculate_nav_series(100000, [0.01, -0.005, 0.02])
        assert len(nav) == 4
        assert nav[0] == 100000

    def test_portfolio_return(self):
        positions = [
            Position("A", quantity=100, current_price=10),
            Position("B", quantity=100, current_price=10),
        ]
        returns = {"A": 0.05, "B": -0.02}
        ret = PortfolioCalculator.calculate_portfolio_return(positions, returns)
        assert abs(ret - 0.015) < 1e-6


# ============ RiskAnalyzer Tests ============

class TestRiskAnalyzer:
    def test_volatility(self):
        returns = [0.01, -0.02, 0.015, 0.005, -0.01, 0.02, -0.005, 0.01]
        vol = RiskAnalyzer.calculate_volatility(returns, annualize=False)
        assert vol > 0

    def test_volatility_annualized(self):
        returns = [0.01] * 100
        vol = RiskAnalyzer.calculate_volatility(returns)
        assert vol >= 0

    def test_max_drawdown(self):
        nav = [100, 110, 105, 95, 100, 90, 95]
        dd = RiskAnalyzer.calculate_max_drawdown(nav)
        assert dd["max_drawdown"] > 0
        assert dd["max_drawdown"] <= 1

    def test_max_drawdown_monotonic_increase(self):
        nav = [100, 110, 120, 130]
        dd = RiskAnalyzer.calculate_max_drawdown(nav)
        assert dd["max_drawdown"] == 0

    def test_sharpe_ratio(self):
        returns = [0.01, -0.005, 0.02, 0.015, -0.01, 0.005, 0.01, -0.003]
        sharpe = RiskAnalyzer.calculate_sharpe_ratio(returns)
        assert isinstance(sharpe, float)

    def test_sortino_ratio(self):
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.003]
        sortino = RiskAnalyzer.calculate_sortino_ratio(returns)
        assert isinstance(sortino, float)

    def test_calmar_ratio(self):
        ratio = RiskAnalyzer.calculate_calmar_ratio(0.2, 0.1)
        assert abs(ratio - 2.0) < 1e-6

    def test_calmar_zero_drawdown(self):
        ratio = RiskAnalyzer.calculate_calmar_ratio(0.2, 0)
        assert ratio == 0

    def test_var(self):
        returns = list(np.random.randn(100) * 0.02)
        var = RiskAnalyzer.calculate_var(returns, 0.95)
        assert var > 0

    def test_beta(self):
        np.random.seed(42)
        port = list(np.random.randn(50) * 0.02)
        bench = list(np.random.randn(50) * 0.015)
        beta = RiskAnalyzer.calculate_beta(port, bench)
        assert isinstance(beta, float)

    def test_full_analysis(self):
        np.random.seed(42)
        returns = list(np.random.randn(50) * 0.02)
        nav = [100000]
        for r in returns:
            nav.append(nav[-1] * (1 + r))

        analysis = RiskAnalyzer.full_analysis(returns, nav)
        assert "volatility" in analysis
        assert "sharpe_ratio" in analysis
        assert "max_drawdown" in analysis
        assert "annual_return" in analysis


# ============ PortfolioManager Tests ============

class TestPortfolioManager:
    def test_initialize(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        assert pm.cash == 100000
        assert pm.total_assets == 100000

    def test_buy(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        success = pm.buy("000001", 1000, 10, "平安银行")
        assert success
        assert pm.cash == 90000
        assert pm.position_count == 1

    def test_buy_insufficient_cash(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(1000)
        success = pm.buy("000001", 1000, 10)
        assert not success

    def test_sell(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        pm.buy("000001", 1000, 10)
        success = pm.sell("000001", 500, 12)
        assert success
        assert pm.cash == 90000 + 6000

    def test_sell_insufficient_position(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        pm.buy("000001", 100, 10)
        success = pm.sell("000001", 200, 12)
        assert not success

    def test_sell_unknown_symbol(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        success = pm.sell("999999", 100, 10)
        assert not success

    def test_update_prices(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        pm.buy("000001", 1000, 10)
        pm.update_prices({"000001": 12})
        assert pm.positions[0].current_price == 12
        assert pm.total_assets == 100000 + 2000

    def test_get_snapshot(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        pm.buy("000001", 1000, 10)
        snapshot = pm.get_snapshot()
        assert snapshot.total_assets == 100000
        assert snapshot.position_count == 1

    def test_record_nav_and_performance(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        pm.buy("000001", 1000, 10)
        pm.record_nav()

        pm.update_prices({"000001": 12})
        pm.record_nav()

        perf = pm.get_performance()
        assert perf["total_assets"] == 102000
        assert perf["position_count"] == 1

    def test_to_dict(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        d = pm.to_dict()
        assert d["portfolio_id"] == 1
        assert d["name"] == "Test"
        assert d["cash"] == 100000

    def test_average_cost_on_multiple_buys(self):
        pm = PortfolioManager(1, "Test")
        pm.initialize(100000)
        pm.buy("000001", 1000, 10)
        pm.buy("000001", 1000, 12)
        pos = pm._positions["000001"]
        assert pos.quantity == 2000
        assert abs(pos.cost_price - 11.0) < 1e-6
