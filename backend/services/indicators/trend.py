# -*- coding: utf-8 -*-
"""
趋势型技术指标

包含：SMA, EMA, MACD, BOLL, TRIX, DEMA
"""
import numpy as np
from typing import List
from .base import BaseIndicator, IndicatorResult, BarData


class SMA(BaseIndicator):
    """简单移动平均线"""

    name = "SMA"
    description = "简单移动平均线"
    category = "trend"

    def __init__(self, periods: List[int] = None):
        self.periods = periods or [5, 10, 20, 60]

    def calculate(self, data: BarData) -> IndicatorResult:
        values = {}
        for period in self.periods:
            if len(data) < period:
                values[f"sma{period}"] = [0.0] * len(data)
            else:
                sma = self._compute_sma(data.closes, period)
                values[f"sma{period}"] = self._to_list(sma)
        return IndicatorResult(
            name=self.name,
            values=values,
            params={"periods": self.periods},
        )

    @staticmethod
    def _compute_sma(arr: np.ndarray, period: int) -> np.ndarray:
        result = np.full_like(arr, np.nan, dtype=np.float64)
        cumsum = np.cumsum(arr)
        result[period - 1:] = (cumsum[period - 1:] - np.concatenate(([0], cumsum[:-period]))) / period
        return result


class EMA(BaseIndicator):
    """指数移动平均线"""

    name = "EMA"
    description = "指数移动平均线"
    category = "trend"

    def __init__(self, periods: List[int] = None):
        self.periods = periods or [5, 10, 20]

    def calculate(self, data: BarData) -> IndicatorResult:
        values = {}
        for period in self.periods:
            if len(data) < period:
                values[f"ema{period}"] = [0.0] * len(data)
            else:
                ema = self._compute_ema(data.closes, period)
                values[f"ema{period}"] = self._to_list(ema)
        return IndicatorResult(
            name=self.name,
            values=values,
            params={"periods": self.periods},
        )

    @staticmethod
    def _compute_ema(arr: np.ndarray, period: int) -> np.ndarray:
        result = np.full_like(arr, np.nan, dtype=np.float64)
        multiplier = 2.0 / (period + 1)
        result[period - 1] = np.mean(arr[:period])
        for i in range(period, len(arr)):
            result[i] = (arr[i] - result[i - 1]) * multiplier + result[i - 1]
        return result


class MACD(BaseIndicator):
    """MACD指标 (Moving Average Convergence Divergence)"""

    name = "MACD"
    description = "平滑异同移动平均线"
    category = "trend"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, data: BarData) -> IndicatorResult:
        min_len = self.slow + self.signal - 1
        if len(data) < min_len:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={
                    "dif": [0.0] * n,
                    "dea": [0.0] * n,
                    "macd_bar": [0.0] * n,
                },
                params={"fast": self.fast, "slow": self.slow, "signal": self.signal},
            )

        ema_fast = EMA._compute_ema(data.closes, self.fast)
        ema_slow = EMA._compute_ema(data.closes, self.slow)
        dif = ema_fast - ema_slow

        # 计算DEA (DIF的EMA)
        valid_start = self.slow - 1
        dif_valid = dif[valid_start:]
        dea_valid = np.full_like(dif_valid, np.nan, dtype=np.float64)
        multiplier = 2.0 / (self.signal + 1)
        dea_valid[self.signal - 1] = np.nanmean(dif_valid[:self.signal])
        for i in range(self.signal, len(dif_valid)):
            dea_valid[i] = (dif_valid[i] - dea_valid[i - 1]) * multiplier + dea_valid[i - 1]

        # 完整长度的DEA
        dea = np.full_like(dif, np.nan, dtype=np.float64)
        dea[valid_start:] = dea_valid

        macd_bar = 2.0 * (dif - dea)

        return IndicatorResult(
            name=self.name,
            values={
                "dif": self._to_list(dif),
                "dea": self._to_list(dea),
                "macd_bar": self._to_list(macd_bar),
            },
            params={"fast": self.fast, "slow": self.slow, "signal": self.signal},
        )


class BOLL(BaseIndicator):
    """布林带指标"""

    name = "BOLL"
    description = "布林带"
    category = "trend"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"upper": [0.0] * n, "middle": [0.0] * n, "lower": [0.0] * n},
                params={"period": self.period, "std_dev": self.std_dev},
            )

        middle = SMA._compute_sma(data.closes, self.period)

        # 计算标准差
        std = np.full_like(data.closes, np.nan, dtype=np.float64)
        for i in range(self.period - 1, len(data)):
            window = data.closes[i - self.period + 1:i + 1]
            std[i] = np.std(window, ddof=0)

        upper = middle + self.std_dev * std
        lower = middle - self.std_dev * std

        return IndicatorResult(
            name=self.name,
            values={
                "upper": self._to_list(upper),
                "middle": self._to_list(middle),
                "lower": self._to_list(lower),
            },
            params={"period": self.period, "std_dev": self.std_dev},
        )


class TRIX(BaseIndicator):
    """三重指数平滑移动平均"""

    name = "TRIX"
    description = "三重指数平滑移动平均"
    category = "trend"

    def __init__(self, period: int = 12):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period * 3:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"trix": [0.0] * n, "ma_trix": [0.0] * n},
                params={"period": self.period},
            )

        # 三次EMA
        ema1 = EMA._compute_ema(data.closes, self.period)
        ema2 = EMA._compute_ema(np.nan_to_num(ema1, nan=0), self.period)
        ema3 = EMA._compute_ema(np.nan_to_num(ema2, nan=0), self.period)

        # TRIX = (EMA3_today - EMA3_yesterday) / EMA3_yesterday * 100
        trix = np.zeros_like(data.closes)
        for i in range(1, len(ema3)):
            if ema3[i - 1] != 0:
                trix[i] = (ema3[i] - ema3[i - 1]) / ema3[i - 1] * 100

        ma_trix = SMA._compute_sma(trix, 9)

        return IndicatorResult(
            name=self.name,
            values={"trix": self._to_list(trix), "ma_trix": self._to_list(ma_trix)},
            params={"period": self.period},
        )


class DEMA(BaseIndicator):
    """双指数移动平均线"""

    name = "DEMA"
    description = "双指数移动平均线"
    category = "trend"

    def __init__(self, period: int = 20):
        self.period = period

    def calculate(self, data: BarData) -> IndicatorResult:
        if len(data) < self.period * 2:
            n = len(data)
            return IndicatorResult(
                name=self.name,
                values={"dema": [0.0] * n},
                params={"period": self.period},
            )

        ema1 = EMA._compute_ema(data.closes, self.period)
        ema2 = EMA._compute_ema(np.nan_to_num(ema1, nan=0), self.period)
        dema = 2 * ema1 - ema2

        return IndicatorResult(
            name=self.name,
            values={"dema": self._to_list(dema)},
            params={"period": self.period},
        )
