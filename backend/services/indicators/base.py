# -*- coding: utf-8 -*-
"""
技术指标基类和数据结构
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class IndicatorResult:
    """指标计算结果"""
    name: str
    values: Dict[str, List[float]]
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "params": self.params,
            "values": self.values,
        }

    def latest(self) -> Dict[str, Optional[float]]:
        """获取最新值"""
        return {
            key: vals[-1] if vals else None
            for key, vals in self.values.items()
        }


@dataclass
class BarData:
    """K线数据"""
    opens: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    volumes: np.ndarray
    amounts: Optional[np.ndarray] = None

    @classmethod
    def from_dicts(cls, bars: List[Dict]) -> "BarData":
        """从字典列表创建"""
        if not bars:
            return cls(
                opens=np.array([]),
                highs=np.array([]),
                lows=np.array([]),
                closes=np.array([]),
                volumes=np.array([]),
            )
        return cls(
            opens=np.array([b.get("open", 0) for b in bars], dtype=np.float64),
            highs=np.array([b.get("high", 0) for b in bars], dtype=np.float64),
            lows=np.array([b.get("low", 0) for b in bars], dtype=np.float64),
            closes=np.array([b.get("close", 0) for b in bars], dtype=np.float64),
            volumes=np.array([b.get("volume", 0) for b in bars], dtype=np.float64),
            amounts=np.array([b.get("amount", 0) for b in bars], dtype=np.float64)
            if "amount" in bars[0] else None,
        )

    def __len__(self) -> int:
        return len(self.closes)


class BaseIndicator(ABC):
    """技术指标基类"""

    name: str = "base"
    description: str = ""
    category: str = ""

    @abstractmethod
    def calculate(self, data: BarData) -> IndicatorResult:
        """计算指标"""
        ...

    def _validate(self, data: BarData, min_length: int = 1) -> bool:
        """验证数据是否足够"""
        return len(data) >= min_length

    @staticmethod
    def _safe_divide(a: np.ndarray, b: np.ndarray, fill: float = 0.0) -> np.ndarray:
        """安全除法，避免除以零"""
        result = np.full_like(a, fill, dtype=np.float64)
        mask = b != 0
        result[mask] = a[mask] / b[mask]
        return result

    @staticmethod
    def _to_list(arr: np.ndarray) -> List[float]:
        """转为列表"""
        return np.nan_to_num(arr, nan=0.0).tolist()
