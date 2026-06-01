# -*- coding: utf-8 -*-
"""
风险分析器
"""
import numpy as np
from typing import List, Dict, Any, Optional


class RiskAnalyzer:
    """组合风险分析器"""

    @staticmethod
    def calculate_volatility(returns: List[float], annualize: bool = True) -> float:
        """计算波动率"""
        if len(returns) < 2:
            return 0
        std = np.std(returns, ddof=1)
        if annualize:
            std *= np.sqrt(252)
        return float(std)

    @staticmethod
    def calculate_max_drawdown(nav_series: List[float]) -> Dict[str, float]:
        """计算最大回撤"""
        if len(nav_series) < 2:
            return {"max_drawdown": 0, "peak_index": 0, "trough_index": 0}

        nav = np.array(nav_series)
        peak = nav[0]
        max_dd = 0
        peak_idx = 0
        trough_idx = 0

        running_peak_idx = 0
        for i in range(1, len(nav)):
            if nav[i] > peak:
                peak = nav[i]
                running_peak_idx = i
            dd = (peak - nav[i]) / peak
            if dd > max_dd:
                max_dd = dd
                peak_idx = running_peak_idx
                trough_idx = i

        return {
            "max_drawdown": float(max_dd),
            "peak_index": peak_idx,
            "trough_index": trough_idx,
        }

    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float],
        risk_free_rate: float = 0.03,
    ) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0
        mean_ret = np.mean(returns) * 252
        std_ret = np.std(returns, ddof=1) * np.sqrt(252)
        if std_ret == 0:
            return 0
        return float((mean_ret - risk_free_rate) / std_ret)

    @staticmethod
    def calculate_sortino_ratio(
        returns: List[float],
        risk_free_rate: float = 0.03,
    ) -> float:
        """计算索提诺比率"""
        if len(returns) < 2:
            return 0
        mean_ret = np.mean(returns) * 252
        downside = [r for r in returns if r < 0]
        if not downside:
            return float("inf") if mean_ret > risk_free_rate else 0
        downside_std = np.std(downside, ddof=1) * np.sqrt(252)
        if downside_std == 0:
            return 0
        return float((mean_ret - risk_free_rate) / downside_std)

    @staticmethod
    def calculate_calmar_ratio(
        annual_return: float,
        max_drawdown: float,
    ) -> float:
        """计算卡尔玛比率"""
        if max_drawdown == 0:
            return 0
        return annual_return / max_drawdown

    @staticmethod
    def calculate_var(
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """计算VaR (Value at Risk)"""
        if len(returns) < 10:
            return 0
        returns_arr = np.array(returns)
        return float(-np.percentile(returns_arr, (1 - confidence) * 100))

    @staticmethod
    def calculate_beta(
        portfolio_returns: List[float],
        benchmark_returns: List[float],
    ) -> float:
        """计算Beta"""
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 0
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        p = np.array(portfolio_returns[:min_len])
        b = np.array(benchmark_returns[:min_len])
        cov = np.cov(p, b)
        var_b = np.var(b, ddof=1)
        if var_b == 0:
            return 0
        return float(cov[0, 1] / var_b)

    @staticmethod
    def full_analysis(
        returns: List[float],
        nav_series: Optional[List[float]] = None,
        benchmark_returns: Optional[List[float]] = None,
        risk_free_rate: float = 0.03,
    ) -> Dict[str, Any]:
        """完整风险分析"""
        analysis = {
            "volatility": RiskAnalyzer.calculate_volatility(returns),
            "sharpe_ratio": RiskAnalyzer.calculate_sharpe_ratio(returns, risk_free_rate),
            "sortino_ratio": RiskAnalyzer.calculate_sortino_ratio(returns, risk_free_rate),
            "var_95": RiskAnalyzer.calculate_var(returns, 0.95),
        }

        if nav_series and len(nav_series) >= 2:
            dd_info = RiskAnalyzer.calculate_max_drawdown(nav_series)
            analysis["max_drawdown"] = dd_info["max_drawdown"]
            cum_ret = (nav_series[-1] - nav_series[0]) / nav_series[0]
            annual_ret = PortfolioCalculator.calculate_annual_return(cum_ret, len(nav_series) - 1)
            analysis["annual_return"] = float(annual_ret)
            analysis["calmar_ratio"] = RiskAnalyzer.calculate_calmar_ratio(
                annual_ret, dd_info["max_drawdown"]
            )

        if benchmark_returns:
            analysis["beta"] = RiskAnalyzer.calculate_beta(returns, benchmark_returns)
            analysis["alpha"] = analysis.get("annual_return", 0) - (
                risk_free_rate + analysis.get("beta", 0) * (
                    np.mean(benchmark_returns) * 252 - risk_free_rate
                )
            )

        return analysis


# 避免循环导入，延迟引用
from .calculator import PortfolioCalculator
