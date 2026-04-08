# -*- coding: utf-8 -*-
"""
集成测试 - 验证新模块之间的协作
"""
import pytest
import numpy as np
from backend.services.indicators import IndicatorCalculator
from backend.services.indicators.base import BarData
from backend.services.screener import ScreenerEngine
from backend.services.screener.filters import FieldCondition
from backend.services.portfolio import PortfolioManager, PortfolioCalculator, RiskAnalyzer
from backend.services.backtest import BacktestEngine
from backend.services.backtest.strategy import DualMAStrategy, RSIStrategy
from backend.services.backtest.models import Bar


# ============ Indicators + Screener Integration ============

class TestIndicatorScreenerIntegration:
    """技术指标与选股系统的集成"""

    def test_calculate_indicators_then_screen(self):
        """计算指标后用结果进行选股"""
        # 模拟K线数据
        np.random.seed(42)
        n = 100
        closes = 10 + np.cumsum(np.random.randn(n) * 0.3)
        data = BarData(
            opens=closes + np.random.randn(n) * 0.1,
            highs=closes + np.abs(np.random.randn(n) * 0.2),
            lows=closes - np.abs(np.random.randn(n) * 0.2),
            closes=closes,
            volumes=np.random.randint(1000, 100000, n).astype(np.float64),
        )

        # 计算指标
        calc = IndicatorCalculator()
        results = calc.calculate(data, ["SMA", "RSI", "MACD"])

        # 验证指标计算成功
        assert "SMA" in results
        assert "RSI" in results
        assert "MACD" in results

        # 使用指标值构建股票数据
        latest_sma5 = results["SMA"].latest().get("sma5", 0) or 0
        latest_rsi6 = results["RSI"].latest().get("rsi6", 50) or 50
        latest_dif = results["MACD"].latest().get("dif", 0) or 0

        # 创建模拟股票数据（含指标值）
        stocks = [
            {"symbol": "TEST1", "name": "测试1", "price": 10, "pe": 15,
             "rsi6": latest_rsi6, "ma5": latest_sma5, "macd_dif": latest_dif},
            {"symbol": "TEST2", "name": "测试2", "price": 20, "pe": 50,
             "rsi6": 75, "ma5": 19, "macd_dif": -0.5},
        ]

        # 用指标条件进行选股
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<=", 30))
        result = engine.screen(stocks)
        assert len(result) == 1
        assert result[0]["symbol"] == "TEST1"


# ============ Portfolio + Risk Integration ============

class TestPortfolioRiskIntegration:
    """组合管理与风险分析的集成"""

    def test_portfolio_with_risk_analysis(self):
        """组合操作后进行风险分析"""
        pm = PortfolioManager(1, "测试组合")
        pm.initialize(100000)

        # 买入股票
        pm.buy("000001", 1000, 10, "平安银行")
        pm.buy("000333", 500, 50, "美的集团")

        # 模拟几个交易日的净值变化
        np.random.seed(42)
        for _ in range(30):
            prices = {
                "000001": 10 * (1 + np.random.randn() * 0.03),
                "000333": 50 * (1 + np.random.randn() * 0.02),
            }
            pm.update_prices(prices)
            pm.record_nav()

        # 获取绩效
        perf = pm.get_performance()
        assert perf["total_assets"] > 0
        assert perf["position_count"] == 2
        assert "risk_metrics" in perf

        # 验证风险指标
        risk = perf["risk_metrics"]
        assert "volatility" in risk
        assert "sharpe_ratio" in risk
        assert "max_drawdown" in risk


# ============ Backtest Full Pipeline ============

class TestBacktestFullPipeline:
    """回测全流程集成测试"""

    def _create_bars(self, count=200, symbol="TEST"):
        np.random.seed(42)
        bars = []
        price = 10.0
        for i in range(count):
            change = np.random.randn() * 0.02
            open_p = price
            close_p = price * (1 + change)
            high_p = max(open_p, close_p) * (1 + abs(np.random.randn() * 0.005))
            low_p = min(open_p, close_p) * (1 - abs(np.random.randn() * 0.005))
            bars.append(Bar(
                symbol=symbol,
                timestamp=f"2024-{(i // 22) + 1:02d}-{(i % 22) + 1:02d}",
                open=round(open_p, 2),
                high=round(high_p, 2),
                low=round(low_p, 2),
                close=round(close_p, 2),
                volume=100000,
            ))
            price = close_p
        return bars

    def test_dual_ma_backtest(self):
        """双均线策略回测完整流程"""
        engine = BacktestEngine(initial_capital=100000, commission_rate=0.0003)
        strategy = DualMAStrategy(fast=5, slow=20)
        bars = self._create_bars(200)

        result = engine.run(strategy, bars)

        assert result.strategy_name == "DualMA"
        assert result.initial_capital == 100000
        assert result.final_capital > 0
        assert isinstance(result.total_return, float)
        assert isinstance(result.max_drawdown, float)
        assert 0 <= result.max_drawdown <= 1
        assert isinstance(result.sharpe_ratio, float)
        assert result.total_trades >= 0

    def test_rsi_backtest(self):
        """RSI策略回测完整流程"""
        engine = BacktestEngine(initial_capital=100000)
        strategy = RSIStrategy(period=14, oversold=30, overbought=70)
        bars = self._create_bars(200)

        result = engine.run(strategy, bars)

        assert result.strategy_name == "RSI"
        assert result.final_capital > 0

    def test_backtest_result_serialization(self):
        """回测结果序列化"""
        engine = BacktestEngine(initial_capital=100000)
        bars = self._create_bars(100)
        result = engine.run(DualMAStrategy(), bars)

        d = result.to_dict()
        assert "strategy_name" in d
        assert "total_return" in d
        assert "equity_curve" in d
        assert "trades" in d
        assert isinstance(d["trades"], list)


# ============ Cross-Module Integration ============

class TestCrossModuleIntegration:
    """跨模块集成测试"""

    def test_indicators_to_screener_to_portfolio(self):
        """完整流程：计算指标 -> 选股 -> 创建组合"""

        # 1. 准备带指标的股票数据
        stocks = [
            {"symbol": "000001", "name": "平安银行", "price": 12, "pe": 6, "roe": 12,
             "rsi6": 55, "ma5": 12.3, "ma10": 12.0},
            {"symbol": "000333", "name": "美的集团", "price": 55, "pe": 15, "roe": 25,
             "rsi6": 62, "ma5": 54.5, "ma10": 53.0},
            {"symbol": "600519", "name": "贵州茅台", "price": 1800, "pe": 35, "roe": 30,
             "rsi6": 70, "ma5": 1790, "ma10": 1780},
        ]

        # 2. 选股
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<=", 20))
        engine.add_condition(FieldCondition("roe", ">=", 15))
        selected = engine.screen(stocks, sort_by="roe", sort_order="desc")

        assert len(selected) == 1
        assert selected[0]["symbol"] == "000333"

        # 3. 将选中股票加入组合
        pm = PortfolioManager(1, "价值成长组合")
        pm.initialize(1000000)

        stock = selected[0]
        qty = int(pm.cash * 0.3 / stock["price"] / 100) * 100
        success = pm.buy(stock["symbol"], qty, stock["price"], stock["name"])
        assert success

        # 验证组合状态
        assert pm.position_count == 1
        # total_assets = cash + position.market_value (cost_price * qty)
        assert pm.cash < 1000000  # 部分资金已用于买入

    def test_backtest_then_portfolio_analysis(self):
        """回测 -> 用结果分析组合风险"""
        # 运行回测
        engine = BacktestEngine(initial_capital=100000)
        np.random.seed(42)
        bars = []
        price = 10.0
        for i in range(100):
            bars.append(Bar(
                symbol="TEST", timestamp=f"t{i}",
                open=price, high=price * 1.01, low=price * 0.99,
                close=price * (1 + np.random.randn() * 0.02),
                volume=100000,
            ))
            price = bars[-1].close

        result = engine.run(DualMAStrategy(fast=5, slow=20), bars)

        # 使用净值曲线做风险分析
        if len(result.equity_curve) > 10:
            returns = []
            for i in range(1, len(result.equity_curve)):
                prev = result.equity_curve[i - 1]
                if prev > 0:
                    returns.append((result.equity_curve[i] - prev) / prev)

            if len(returns) > 5:
                analysis = RiskAnalyzer.full_analysis(
                    returns, result.equity_curve
                )
                assert "volatility" in analysis
                assert "sharpe_ratio" in analysis
