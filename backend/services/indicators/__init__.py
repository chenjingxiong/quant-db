# -*- coding: utf-8 -*-
"""
技术指标计算模块

提供常用技术指标的计算功能：
- 趋势型：SMA, EMA, MACD, BOLL, TRIX, DEMA
- 震荡型：KDJ, RSI, CCI, WR, ROC
- 能量型：OBV, VR, EMV
- 波动型：ATR, SAR
"""
from .base import BaseIndicator, IndicatorResult
from .trend import SMA, EMA, MACD, BOLL, TRIX, DEMA
from .oscillator import KDJ, RSI, CCI, WR, ROC
from .volume import OBV, VR, EMV
from .volatility import ATR, SAR
from .calculator import IndicatorCalculator

__all__ = [
    "BaseIndicator", "IndicatorResult",
    "SMA", "EMA", "MACD", "BOLL", "TRIX", "DEMA",
    "KDJ", "RSI", "CCI", "WR", "ROC",
    "OBV", "VR", "EMV",
    "ATR", "SAR",
    "IndicatorCalculator",
]
