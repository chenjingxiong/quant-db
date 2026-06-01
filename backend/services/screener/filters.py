# -*- coding: utf-8 -*-
"""
选股条件过滤器
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np
from loguru import logger


class BaseFilter(ABC):
    """过滤器基类"""

    name: str = "base"

    @abstractmethod
    def apply(self, stock_data: Dict[str, Any]) -> bool:
        """判断股票是否满足条件"""
        ...

    @abstractmethod
    def get_description(self) -> str:
        """获取条件描述"""
        ...


class FieldCondition(BaseFilter):
    """字段条件过滤器"""

    name = "field_condition"

    OPERATORS = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
        "between": lambda a, b: b[0] <= a <= b[1],
    }

    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator
        self.value = value

        if operator not in self.OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")

    def apply(self, stock_data: Dict[str, Any]) -> bool:
        field_value = stock_data.get(self.field)
        if field_value is None:
            return False
        try:
            return self.OPERATORS[self.operator](field_value, self.value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Filter apply error: {e}")
            return False

    def get_description(self) -> str:
        return f"{self.field} {self.operator} {self.value}"


class CrossFieldCondition(BaseFilter):
    """跨字段条件过滤器 - 比较两个字段的值"""

    name = "cross_field_condition"

    OPERATORS = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
    }

    def __init__(self, field_a: str, operator: str, field_b: str):
        self.field_a = field_a
        self.operator = operator
        self.field_b = field_b

        if operator not in self.OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")

    def apply(self, stock_data: Dict[str, Any]) -> bool:
        val_a = stock_data.get(self.field_a)
        val_b = stock_data.get(self.field_b)
        if val_a is None or val_b is None:
            return False
        try:
            return self.OPERATORS[self.operator](val_a, val_b)
        except (TypeError, ValueError) as e:
            logger.warning(f"CrossField filter error: {e}")
            return False

    def get_description(self) -> str:
        return f"{self.field_a} {self.operator} {self.field_b}"


class BasicFilter:
    """基础条件筛选器"""

    @staticmethod
    def create_conditions(criteria: Dict[str, Any]) -> List[FieldCondition]:
        """从条件字典创建过滤器列表"""
        conditions = []
        field_map = {
            "market_cap": "market_cap",
            "pe": "pe",
            "pb": "pb",
            "price": "price",
            "volume": "volume",
            "change_percent": "change_percent",
            "turnover_rate": "turnover_rate",
            "amplitude": "amplitude",
        }

        for key, condition in criteria.items():
            if key in field_map:
                field = field_map[key]
                op = condition.get("operator", ">=")
                val = condition.get("value")
                if val is not None:
                    conditions.append(FieldCondition(field, op, val))

        return conditions


class TechnicalFilter:
    """技术指标筛选器"""

    @staticmethod
    def create_conditions(criteria: Dict[str, Any]) -> List[FieldCondition]:
        conditions = []
        tech_fields = {
            "ma5_gt_ma10": None,  # special handling
            "ma10_gt_ma20": None,
            "rsi_oversold": None,
            "rsi_overbought": None,
            "macd_golden_cross": None,
            "boll_squeeze": None,
        }

        for key, val in criteria.items():
            if key == "ma5_gt_ma10" and val:
                conditions.append(CrossFieldCondition("ma5", ">", "ma10"))
            elif key == "ma10_gt_ma20" and val:
                conditions.append(CrossFieldCondition("ma10", ">", "ma20"))
            elif key == "rsi_oversold":
                conditions.append(FieldCondition("rsi6", "<", val if isinstance(val, (int, float)) else 30))
            elif key == "rsi_overbought":
                conditions.append(FieldCondition("rsi6", ">", val if isinstance(val, (int, float)) else 70))
            elif key == "macd_golden_cross" and val:
                conditions.append(FieldCondition("macd_dif", ">", 0))
            elif key == "volume_ratio":
                op = val.get("operator", ">=") if isinstance(val, dict) else ">="
                v = val.get("value", 2.0) if isinstance(val, dict) else val
                conditions.append(FieldCondition("volume_ratio", op, v))

        return conditions


class FinancialFilter:
    """财务指标筛选器"""

    @staticmethod
    def create_conditions(criteria: Dict[str, Any]) -> List[FieldCondition]:
        conditions = []
        financial_fields = {
            "pe": "pe",
            "pb": "pb",
            "roe": "roe",
            "revenue_growth": "revenue_growth",
            "profit_growth": "profit_growth",
            "gross_margin": "gross_margin",
            "net_margin": "net_margin",
            "debt_ratio": "debt_ratio",
            "dividend_yield": "dividend_yield",
        }

        for key, condition in criteria.items():
            if key in financial_fields:
                field = financial_fields[key]
                op = condition.get("operator", ">=") if isinstance(condition, dict) else ">="
                val = condition.get("value", condition) if isinstance(condition, dict) else condition
                conditions.append(FieldCondition(field, op, val))

        return conditions
