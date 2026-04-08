# -*- coding: utf-8 -*-
"""
能量型技术指标

包含：OBV, VR, EMV
"""
import numpy as np
from .base import BaseIndicator, IndicatorResult, BarData


class OBV(BaseIndicator):
    """能量潮指标 (On Balance Volume)"""

    name = "OBV"
    description = "能量潮指标"
    category = "volume"

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < 2:
            return IndicatorResult(
                name=self.name,
                values={"obv": [0.0] * len(data)},
            )

        obv = np.zeros(len(data))
        for i in range(1, len(data)):
            if data.closes[i] > data.closes[i - 1]:
                obv[i] = obv[i - 1] + data.volumes[i]
            elif data.closes[i] < data.closes[i - 1]:
                obv[i] = obv[i - 1] - data.volumes[i]
            else:
                obv[i] = obv[i - 1]

        return IndicatorResult(
            name=self.name,
            values={"obv": self._to_list(obv)},
        )


class VR(BaseIndicator):
    """容量比率指标 (Volume Ratio)"""

    name = "VR"
    description = "容量比率指标"
    category = "volume"

    def __init__(self, period: int = 26):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period + 1:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"vr": [100.0] * n},
                params={"period": self.period},
            )

        vr = np.full(len(data), 100.0)

        for i in range(self.period, len(data)):
            up_vol = 0.0
            down_vol = 0.0
            eq_vol = 0.0

            for j in range(i - self.period + 1, i + 1):
                if data.closes[j] > data.closes[j - 1]:
                    up_vol += data.volumes[j]
                elif data.closes[j] < data.closes[j - 1]:
                    down_vol += data.volumes[j]
                else:
                    eq_vol += data.volumes[j]

            if down_vol + eq_vol / 2 > 0:
                vr[i] = (up_vol + eq_vol / 2) / (down_vol + eq_vol / 2) * 100

        return IndicatorResult(
            name=self.name,
            values={"vr": self._to_list(vr)},
            params={"period": self.period},
        )


class EMV(BaseIndicator):
    """简易波动指标 (Ease of Movement)"""

    name = "EMV"
    description = "简易波动指标"
    category = "volume"

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < 2:
            return IndicatorResult(
                name=self.name,
                values={"emv": [0.0] * len(data), "ma_emv": [0.0] * len(data)},
                params={"period": self.period},
            )

        emv = np.zeros(len(data))

        for i in range(1, len(data)):
            mid_move = (data.highs[i] + data.lows[i]) / 2 - (data.highs[i - 1] + data.lows[i - 1]) / 2
            box_ratio = data.volumes[i] / 10000
            high_low_diff = data.highs[i] - data.lows[i]

            if high_low_diff > 0 and box_ratio > 0:
                emv[i] = mid_move * high_low_diff / box_ratio

        # MA of EMV
        ma_emv = np.zeros(len(data))
        for i in range(self.period - 1, len(data)):
            ma_emv[i] = np.mean(emv[i - self.period + 1:i + 1])

        return IndicatorResult(
            name=self.name,
            values={"emv": self._to_list(emv), "ma_emv": self._to_list(ma_emv)},
            params={"period": self.period},
        )
