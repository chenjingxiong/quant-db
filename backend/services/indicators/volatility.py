# -*- coding: utf-8 -*-
"""
波动型技术指标

包含：ATR, SAR
"""
import numpy as np
from .base import BaseIndicator, IndicatorResult, BarData
from .trend import SMA


class ATR(BaseIndicator):
    """真实波幅均值 (Average True Range)"""

    name = "ATR"
    description = "真实波幅均值"
    category = "volatility"

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period + 1:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"atr": [0.0] * n},
                params={"period": self.period},
            )

        tr = np.zeros(len(data))
        tr[0] = data.highs[0] - data.lows[0]

        for i in range(1, len(data)):
            tr[i] = max(
                data.highs[i] - data.lows[i],
                abs(data.highs[i] - data.closes[i - 1]),
                abs(data.lows[i] - data.closes[i - 1]),
            )

        atr = np.zeros(len(data))
        atr[self.period - 1] = np.mean(tr[:self.period])
        for i in range(self.period, len(data)):
            atr[i] = (atr[i - 1] * (self.period - 1) + tr[i]) / self.period

        return IndicatorResult(
            name=self.name,
            values={"atr": self._to_list(atr)},
            params={"period": self.period},
        )


class SAR(BaseIndicator):
    """抛物线指标 (Stop and Reverse)"""

    name = "SAR"
    description = "抛物线指标"
    category = "volatility"

    def __init__(self, af_step: float = 0.02, af_max: float = 0.2):
        self.af_step = af_step
        self.af_max = af_max

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < 2:
            return IndicatorResult(
                name=self.name,
                values={"sar": [0.0] * len(data)},
                params={"af_step": self.af_step, "af_max": self.af_max},
            )

        n = len(data)
        sar = np.zeros(n)
        af = self.af_step
        is_long = data.closes[1] > data.closes[0]

        if is_long:
            ep = data.highs[0]
            sar[0] = data.lows[0]
        else:
            ep = data.lows[0]
            sar[0] = data.highs[0]

        for i in range(1, n):
            sar[i] = sar[i - 1] + af * (ep - sar[i - 1])

            if is_long:
                sar[i] = min(sar[i], data.lows[i - 1])
                if i >= 2:
                    sar[i] = min(sar[i], data.lows[i - 2])

                if data.lows[i] < sar[i]:
                    is_long = False
                    sar[i] = ep
                    ep = data.lows[i]
                    af = self.af_step
                else:
                    if data.highs[i] > ep:
                        ep = data.highs[i]
                        af = min(af + self.af_step, self.af_max)
            else:
                sar[i] = max(sar[i], data.highs[i - 1])
                if i >= 2:
                    sar[i] = max(sar[i], data.highs[i - 2])

                if data.highs[i] > sar[i]:
                    is_long = True
                    sar[i] = ep
                    ep = data.highs[i]
                    af = self.af_step
                else:
                    if data.lows[i] < ep:
                        ep = data.lows[i]
                        af = min(af + self.af_step, self.af_max)

        return IndicatorResult(
            name=self.name,
            values={"sar": self._to_list(sar)},
            params={"af_step": self.af_step, "af_max": self.af_max},
        )
