# -*- coding: utf-8 -*-
"""
震荡型技术指标

包含：KDJ, RSI, CCI, WR, ROC
"""
import numpy as np
from .base import BaseIndicator, IndicatorResult, BarData


class KDJ(BaseIndicator):
    """KDJ随机指标"""

    name = "KDJ"
    description = "随机指标"
    category = "oscillator"

    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        self.n = n
        self.m1 = m1
        self.m2 = m2

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.n:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"k": [50.0] * n, "d": [50.0] * n, "j": [50.0] * n},
                params={"n": self.n, "m1": self.m1, "m2": self.m2},
            )

        closes = data.closes
        highs = data.highs
        lows = data.lows

        k = np.full(len(data), 50.0)
        d = np.full(len(data), 50.0)
        j = np.full(len(data), 50.0)

        for i in range(self.n - 1, len(data)):
            high_n = highs[i - self.n + 1:i + 1]
            low_n = lows[i - self.n + 1:i + 1]
            highest = np.max(high_n)
            lowest = np.min(low_n)

            if highest == lowest:
                rsv = 50.0
            else:
                rsv = (closes[i] - lowest) / (highest - lowest) * 100

            k[i] = (2 / 3) * k[i - 1] + (1 / 3) * rsv
            d[i] = (2 / 3) * d[i - 1] + (1 / 3) * k[i]
            j[i] = 3 * k[i] - 2 * d[i]

        return IndicatorResult(
            name=self.name,
            values={"k": self._to_list(k), "d": self._to_list(d), "j": self._to_list(j)},
            params={"n": self.n, "m1": self.m1, "m2": self.m2},
        )


class RSI(BaseIndicator):
    """相对强弱指标"""

    name = "RSI"
    description = "相对强弱指标"
    category = "oscillator"

    def __init__(self, periods: list = None):
        self.periods = periods or [6, 12, 24]

    def calculate(self, data: BarData) -> IndicatorResult:
        values = {}
        for period in self.periods:
            if len(data) < period + 1:
                values[f"rsi{period}"] = [50.0] * len(data)
            else:
                rsi = self._compute_rsi(data.closes, period)
                values[f"rsi{period}"] = self._to_list(rsi)
        return IndicatorResult(
            name=self.name,
            values=values,
            params={"periods": self.periods},
        )

    @staticmethod
    def _compute_rsi(closes: np.ndarray, period: int) -> np.ndarray:
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(closes))
        avg_loss = np.zeros(len(closes))

        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])

        for i in range(period + 1, len(closes)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

        rsi = np.full(len(closes), 50.0)
        for i in range(period, len(closes)):
            if avg_loss[i] == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain[i] / avg_loss[i]
                rsi[i] = 100 - 100 / (1 + rs)

        return rsi


class CCI(BaseIndicator):
    """商品路径指标"""

    name = "CCI"
    description = "商品路径指标"
    category = "oscillator"

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"cci": [0.0] * n},
                params={"period": self.period},
            )

        tp = (data.highs + data.lows + data.closes) / 3
        cci = np.zeros(len(data))

        for i in range(self.period - 1, len(data)):
            window = tp[i - self.period + 1:i + 1]
            ma = np.mean(window)
            md = np.mean(np.abs(window - ma))
            cci[i] = (tp[i] - ma) / (0.015 * md) if md != 0 else 0

        return IndicatorResult(
            name=self.name,
            values={"cci": self._to_list(cci)},
            params={"period": self.period},
        )


class WR(BaseIndicator):
    """威廉指标"""

    name = "WR"
    description = "威廉指标"
    category = "oscillator"

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"wr": [-50.0] * n},
                params={"period": self.period},
            )

        wr = np.full(len(data), -50.0)

        for i in range(self.period - 1, len(data)):
            high_n = np.max(data.highs[i - self.period + 1:i + 1])
            low_n = np.min(data.lows[i - self.period + 1:i + 1])
            if high_n == low_n:
                wr[i] = -50.0
            else:
                wr[i] = -100 * (high_n - data.closes[i]) / (high_n - low_n)

        return IndicatorResult(
            name=self.name,
            values={"wr": self._to_list(wr)},
            params={"period": self.period},
        )


class ROC(BaseIndicator):
    """变动速率指标"""

    name = "ROC"
    description = "变动速率指标"
    category = "oscillator"

    def __init__(self, period: int = 12):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period + 1:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"roc": [0.0] * n},
                params={"period": self.period},
            )

        roc = np.zeros(len(data))
        for i in range(self.period, len(data)):
            if data.closes[i - self.period] != 0:
                roc[i] = (data.closes[i] - data.closes[i - self.period]) / data.closes[i - self.period] * 100

        return IndicatorResult(
            name=self.name,
            values={"roc": self._to_list(roc)},
            params={"period": self.period},
        )
