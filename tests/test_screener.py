# -*- coding: utf-8 -*-
"""
智能选股系统单元测试
"""
import pytest
from backend.services.screener.engine import ScreenerEngine
from backend.services.screener.filters import (
    FieldCondition, BasicFilter, TechnicalFilter, FinancialFilter,
)


# ============ Fixtures ============

@pytest.fixture
def sample_stocks():
    return [
        {"symbol": "000001", "name": "平安银行", "price": 12.5, "pe": 6.2, "pb": 0.8, "roe": 12.5,
         "market_cap": 2.4e11, "change_percent": 2.5, "volume": 5e8, "turnover_rate": 3.2,
         "rsi6": 55, "ma5": 12.3, "ma10": 12.0, "ma20": 11.8, "macd_dif": 0.15, "volume_ratio": 1.2},
        {"symbol": "000002", "name": "万科A", "price": 8.5, "pe": 8.5, "pb": 1.2, "roe": 15.0,
         "market_cap": 1e11, "change_percent": -1.2, "volume": 3e8, "turnover_rate": 2.1,
         "rsi6": 35, "ma5": 8.8, "ma10": 9.0, "ma20": 9.2, "macd_dif": -0.2, "volume_ratio": 0.8},
        {"symbol": "000333", "name": "美的集团", "price": 55.0, "pe": 15.0, "pb": 4.5, "roe": 25.0,
         "market_cap": 3.8e11, "change_percent": 1.8, "volume": 1e8, "turnover_rate": 1.5,
         "rsi6": 62, "ma5": 54.5, "ma10": 53.0, "ma20": 51.0, "macd_dif": 0.5, "volume_ratio": 1.5},
        {"symbol": "000651", "name": "格力电器", "price": 38.0, "pe": 10.0, "pb": 3.0, "roe": 20.0,
         "market_cap": 2.3e11, "change_percent": -0.5, "volume": 2e8, "turnover_rate": 1.0,
         "rsi6": 45, "ma5": 38.5, "ma10": 39.0, "ma20": 38.0, "macd_dif": -0.1, "volume_ratio": 0.9},
        {"symbol": "600519", "name": "贵州茅台", "price": 1800.0, "pe": 35.0, "pb": 12.0, "roe": 30.0,
         "market_cap": 2.3e12, "change_percent": 0.8, "volume": 5e7, "turnover_rate": 0.5,
         "rsi6": 70, "ma5": 1790.0, "ma10": 1780.0, "ma20": 1750.0, "macd_dif": 2.0, "volume_ratio": 1.1},
    ]


# ============ FieldCondition Tests ============

class TestFieldCondition:
    def test_gt(self, sample_stocks):
        cond = FieldCondition("pe", "<=", 15)
        matches = [cond.apply(s) for s in sample_stocks]
        assert matches == [True, True, True, True, False]

    def test_between(self, sample_stocks):
        cond = FieldCondition("price", "between", [10, 60])
        matches = [cond.apply(s) for s in sample_stocks]
        assert matches == [True, False, True, True, False]

    def test_missing_field(self, sample_stocks):
        cond = FieldCondition("nonexistent", ">", 0)
        assert all(not cond.apply(s) for s in sample_stocks)

    def test_invalid_operator(self):
        with pytest.raises(ValueError):
            FieldCondition("price", "~~", 10)

    def test_description(self):
        cond = FieldCondition("pe", "<=", 30)
        assert cond.get_description() == "pe <= 30"


# ============ BasicFilter Tests ============

class TestBasicFilter:
    def test_create_conditions(self):
        criteria = {
            "pe": {"operator": "<=", "value": 20},
            "price": {"operator": "between", "value": [10, 100]},
        }
        conditions = BasicFilter.create_conditions(criteria)
        assert len(conditions) == 2

    def test_empty_criteria(self):
        conditions = BasicFilter.create_conditions({})
        assert len(conditions) == 0


# ============ TechnicalFilter Tests ============

class TestTechnicalFilter:
    def test_rsi_oversold(self):
        criteria = {"rsi_oversold": 40}
        conditions = TechnicalFilter.create_conditions(criteria)
        assert len(conditions) == 1

    def test_ma_conditions(self):
        criteria = {"ma5_gt_ma10": True, "ma10_gt_ma20": True}
        conditions = TechnicalFilter.create_conditions(criteria)
        assert len(conditions) == 4  # 2 conditions each (value > 0)


# ============ FinancialFilter Tests ============

class TestFinancialFilter:
    def test_create_conditions(self):
        criteria = {
            "roe": {"operator": ">=", "value": 15},
            "pe": {"operator": "<=", "value": 30},
        }
        conditions = FinancialFilter.create_conditions(criteria)
        assert len(conditions) == 2


# ============ ScreenerEngine Tests ============

class TestScreenerEngine:
    def test_basic_screen(self, sample_stocks):
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<=", 15))
        result = engine.screen(sample_stocks)
        assert len(result) == 4  # All except Maotai
        symbols = [s["symbol"] for s in result]
        assert "600519" not in symbols

    def test_and_logic(self, sample_stocks):
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<=", 15))
        engine.add_condition(FieldCondition("roe", ">=", 20))
        result = engine.screen(sample_stocks, logic="and")
        symbols = [s["symbol"] for s in result]
        assert "000333" in symbols
        assert "000651" in symbols

    def test_or_logic(self, sample_stocks):
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<=", 8))
        engine.add_condition(FieldCondition("roe", ">=", 28))
        result = engine.screen(sample_stocks, logic="or")
        symbols = [s["symbol"] for s in result]
        assert "000001" in symbols
        assert "600519" in symbols

    def test_sort_desc(self, sample_stocks):
        engine = ScreenerEngine()
        result = engine.screen(sample_stocks, sort_by="pe", sort_order="desc")
        assert result[0]["pe"] >= result[-1]["pe"]

    def test_sort_asc(self, sample_stocks):
        engine = ScreenerEngine()
        result = engine.screen(sample_stocks, sort_by="pe", sort_order="asc")
        assert result[0]["pe"] <= result[-1]["pe"]

    def test_limit(self, sample_stocks):
        engine = ScreenerEngine()
        result = engine.screen(sample_stocks, limit=2)
        assert len(result) == 2

    def test_no_conditions(self, sample_stocks):
        engine = ScreenerEngine()
        result = engine.screen(sample_stocks)
        assert len(result) == len(sample_stocks)

    def test_set_conditions_from_config(self, sample_stocks):
        config = {
            "basic": {"pe": {"operator": "<=", "value": 20}},
            "financial": {"roe": {"operator": ">=", "value": 15}},
        }
        engine = ScreenerEngine()
        engine.set_conditions_from_config(config)
        assert engine.condition_count == 2
        result = engine.screen(sample_stocks)
        assert len(result) > 0

    def test_clear_conditions(self):
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("price", ">", 10))
        assert engine.condition_count == 1
        engine.clear_conditions()
        assert engine.condition_count == 0

    def test_condition_descriptions(self):
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<=", 30))
        engine.add_condition(FieldCondition("roe", ">=", 15))
        descriptions = engine.get_condition_descriptions()
        assert len(descriptions) == 2
        assert "pe <= 30" in descriptions
        assert "roe >= 15" in descriptions

    def test_all_conditions_no_match(self, sample_stocks):
        engine = ScreenerEngine()
        engine.add_condition(FieldCondition("pe", "<", 1))
        result = engine.screen(sample_stocks)
        assert len(result) == 0
