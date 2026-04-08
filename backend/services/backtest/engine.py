# -*- coding: utf-8 -*-
"""
回测引擎
"""
import numpy as np
from typing import List, Dict, Any, Optional, Type
from datetime import datetime
from loguru import logger

from .models import Bar, BacktestResult, Trade
from .strategy import BaseStrategy
from .broker import SimulatedBroker


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        initial_capital: float = 1000000,
        commission_rate: float = 0.0003,
        slippage: float = 0.0,
    ):
        self.initial_capital = initial_capital
        self.broker = SimulatedBroker(
            commission_rate=commission_rate,
            slippage=slippage,
        )

    def run(
        self,
        strategy: BaseStrategy,
        bars: List[Bar],
    ) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 策略实例
            bars: K线数据列表

        Returns:
            回测结果
        """
        if not bars:
            return self._empty_result(strategy)

        # 初始化
        self.broker.initialize(self.initial_capital)
        strategy.on_init(self.initial_capital)

        symbol = bars[0].symbol
        equity_curve = [self.initial_capital]

        for bar in bars:
            # 策略处理K线
            strategy.on_bar(bar)

            # 执行策略产生的订单
            for order in strategy.pending_orders:
                order.timestamp = bar.timestamp
                self.broker.execute_order(order, bar.close)

                # 更新策略的持仓信息
                self._sync_positions(strategy)

            # 同步现金
            strategy._cash = self.broker.cash

            # 记录净值
            total = self.broker.get_total_assets({symbol: bar.close})
            equity_curve.append(total)

        # 计算结果
        return self._calculate_result(
            strategy=strategy,
            symbol=symbol,
            bars=bars,
            equity_curve=equity_curve,
        )

    def _sync_positions(self, strategy: BaseStrategy):
        """同步持仓信息"""
        from .models import Position as BTPosition
        for symbol, pos in self.broker.positions.items():
            strategy._positions[symbol] = pos

    def _calculate_result(
        self,
        strategy: BaseStrategy,
        symbol: str,
        bars: List[Bar],
        equity_curve: List[float],
    ) -> BacktestResult:
        """计算回测结果"""
        trades = self.broker.trades
        initial = self.initial_capital
        final = equity_curve[-1] if equity_curve else initial

        # 收益率
        total_return = (final - initial) / initial if initial > 0 else 0

        # 年化收益
        days = len(bars)
        annual_return = (1 + total_return) ** (252 / max(days, 1)) - 1 if days > 0 else 0

        # 净值曲线
        nav = np.array(equity_curve)
        returns = np.diff(nav) / nav[:-1] if len(nav) > 1 else np.array([0])
        returns = np.where(np.isfinite(returns), returns, 0)

        # 最大回撤
        peak = np.maximum.accumulate(nav)
        drawdown = (peak - nav) / np.where(peak > 0, peak, 1)
        max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0

        # 夏普比率
        sharpe = 0.0
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = float(np.mean(returns) * 252 / (np.std(returns) * np.sqrt(252)))

        # 胜率
        sell_trades = [t for t in trades if t.side == "sell"]
        winning = sum(1 for t in sell_trades if t.profit_loss > 0)
        losing = sum(1 for t in sell_trades if t.profit_loss <= 0)
        total_sell = len(sell_trades)
        win_rate = winning / total_sell if total_sell > 0 else 0

        # 盈亏比
        total_profit = sum(t.profit_loss for t in sell_trades if t.profit_loss > 0)
        total_loss = abs(sum(t.profit_loss for t in sell_trades if t.profit_loss < 0))
        pl_ratio = total_profit / total_loss if total_loss > 0 else float("inf") if total_profit > 0 else 0

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            start_date=bars[0].timestamp if bars else "",
            end_date=bars[-1].timestamp if bars else "",
            initial_capital=initial,
            final_capital=final,
            total_return=float(total_return),
            annual_return=float(annual_return),
            max_drawdown=float(max_drawdown),
            sharpe_ratio=float(sharpe),
            win_rate=float(win_rate),
            profit_loss_ratio=float(pl_ratio),
            total_trades=len(trades),
            winning_trades=winning,
            losing_trades=losing,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown.tolist(),
        )

    def _empty_result(self, strategy: BaseStrategy) -> BacktestResult:
        return BacktestResult(
            strategy_name=strategy.name,
            symbol="",
            start_date="", end_date="",
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0, annual_return=0, max_drawdown=0,
            sharpe_ratio=0, win_rate=0, profit_loss_ratio=0,
            total_trades=0, winning_trades=0, losing_trades=0,
        )
