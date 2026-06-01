# -*- coding: utf-8 -*-
"""
指标计算引擎

提供统一的指标计算接口
"""
from typing import Dict, List, Any, Optional, Type
from loguru import logger
from .base import BaseIndicator, IndicatorResult, BarData
from .trend import SMA, EMA, MACD, BOLL, TRIX, DEMA
from .oscillator import KDJ, RSI, CCI, WR, ROC
from .volume import OBV, VR, EMV
from .volatility import ATR, SAR


# 指标注册表
INDICATOR_REGISTRY: Dict[str, Type[BaseIndicator]] = {
    "SMA": SMA,
    "EMA": EMA,
    "MACD": MACD,
    "BOLL": BOLL,
    "TRIX": TRIX,
    "DEMA": DEMA,
    "KDJ": KDJ,
    "RSI": RSI,
    "CCI": CCI,
    "WR": WR,
    "ROC": ROC,
    "OBV": OBV,
    "VR": VR,
    "EMV": EMV,
    "ATR": ATR,
    "SAR": SAR,
}


class IndicatorCalculator:
    """指标计算引擎"""

    def __init__(self):
        self._indicators: Dict[str, BaseIndicator] = {}

    def register(self, name: str, indicator: BaseIndicator):
        """注册指标实例"""
        self._indicators[name] = indicator

    def get(self, name: str) -> Optional[BaseIndicator]:
        """获取指标实例"""
        return self._indicators.get(name)

    @staticmethod
    def list_indicators() -> List[Dict[str, str]]:
        """列出所有可用指标"""
        return [
            {"name": cls.name, "description": cls.description, "category": cls.category}
            for cls in INDICATOR_REGISTRY.values()
        ]

    def calculate(
        self,
        data: BarData,
        indicators: Optional[List[str]] = None,
    ) -> Dict[str, IndicatorResult]:
        """
        批量计算指标

        Args:
            data: K线数据
            indicators: 指标名称列表，None表示计算全部

        Returns:
            指标结果字典
        """
        results = {}

        if indicators is None:
            indicators = list(self._indicators.keys())

        for name in indicators:
            indicator = self._indicators.get(name)
            if indicator is None:
                # 尝试从注册表创建默认实例
                cls = INDICATOR_REGISTRY.get(name.upper())
                if cls:
                    indicator = cls()
                    self._indicators[name] = indicator
                else:
                    logger.warning(f"Unknown indicator: {name}")
                    continue

            try:
                result = indicator.calculate(data)
                results[name] = result
            except Exception as e:
                logger.error(f"Calculate indicator {name} failed: {e}")

        return results

    def calculate_all_default(self, data: BarData) -> Dict[str, IndicatorResult]:
        """使用默认参数计算所有指标"""
        if not self._indicators:
            for cls in INDICATOR_REGISTRY.values():
                instance = cls()
                self._indicators[instance.name] = instance

        return self.calculate(data)

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> "IndicatorCalculator":
        """从配置创建计算器"""
        calc = IndicatorCalculator()
        for name, params in config.items():
            cls = INDICATOR_REGISTRY.get(name.upper())
            if cls:
                if params:
                    calc.register(name, cls(**params))
                else:
                    calc.register(name, cls())
        return calc
