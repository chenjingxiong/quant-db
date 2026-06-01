# -*- coding: utf-8 -*-
"""
选股引擎

统一管理筛选条件和执行选股
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from .filters import BaseFilter, FieldCondition, CrossFieldCondition, BasicFilter, TechnicalFilter, FinancialFilter


class ScreenerEngine:
    """选股引擎"""

    def __init__(self):
        self._conditions: List[BaseFilter] = []

    def add_condition(self, condition: BaseFilter):
        """添加筛选条件"""
        self._conditions.append(condition)

    def add_conditions(self, conditions: List[BaseFilter]):
        """批量添加条件"""
        self._conditions.extend(conditions)

    def clear_conditions(self):
        """清空所有条件"""
        self._conditions.clear()

    def set_conditions_from_config(self, config: Dict[str, Any]):
        """从配置设置条件"""
        self.clear_conditions()

        logic = config.get("logic", "and")

        # 基础条件
        if config.get("basic"):
            conditions = BasicFilter.create_conditions(config["basic"])
            self.add_conditions(conditions)

        # 技术指标条件
        if config.get("technical"):
            conditions = TechnicalFilter.create_conditions(config["technical"])
            self.add_conditions(conditions)

        # 财务条件
        if config.get("financial"):
            conditions = FinancialFilter.create_conditions(config["financial"])
            self.add_conditions(conditions)

    def screen(
        self,
        stocks: List[Dict[str, Any]],
        logic: str = "and",
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        执行选股

        Args:
            stocks: 股票数据列表
            logic: 逻辑组合 and/or
            sort_by: 排序字段
            sort_order: 排序方向
            limit: 返回数量限制

        Returns:
            符合条件的股票列表
        """
        if not self._conditions:
            result = list(stocks)
        else:
            result = []
            for stock in stocks:
                matches = []
                for condition in self._conditions:
                    try:
                        matches.append(condition.apply(stock))
                    except Exception:
                        matches.append(False)

                if logic == "and":
                    if all(matches):
                        result.append(stock)
                elif logic == "or":
                    if any(matches):
                        result.append(stock)

        # 排序
        if sort_by and result:
            reverse = sort_order.lower() == "desc"
            result.sort(
                key=lambda x: x.get(sort_by, 0) or 0,
                reverse=reverse,
            )

        # 限制数量
        return result[:limit]

    def get_condition_descriptions(self) -> List[str]:
        """获取所有条件描述"""
        return [c.get_description() for c in self._conditions]

    @property
    def condition_count(self) -> int:
        return len(self._conditions)
