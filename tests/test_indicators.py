# -*- coding: utf-8 -*-
"""
技术指标模块单元测试
"""
import pytest
import numpy as np
from backend.services.indicators.base import BarData, IndicatorResult
from backend.services.indicators.trend import SMA, EMA, MACD, BOLL, TRIX, DEMA
from backend.services.indicators.oscillator import KDJ, RSI, CCI, WR, ROC
from backend.services.indicators.volume import OBV, VR, EMV
from backend.services.indicators.volatility import ATR, SAR
from backend.services.indicators.calculator import IndicatorCalculator


# ============ Fixtures ============

@pytest.fixture
def sample_bars():
    """创建测试用K线数据"""
    np.random.seed(42)
    n = 100
    base_price = 10.0
    close_prices = base_price + np.cumsum(np.random.randn(n) * 0.3)
    opens = close_prices + np.random.randn(n) * 0.1
    highs = np.maximum(opens, close_prices) + np.abs(np.random.randn(n) * 0.2)
    lows = np.minimum(opens, close_prices) - np.abs(np.random.randn(n) * 0.2)
    volumes = np.random.randint(1000, 100000, n).astype(np.float64)

    return BarData(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=close_prices,
        volumes=volumes,
    )


@pytest.fixture
def short_bars():
    """短数据集"""
    return BarData(
        opens=np.array([10.0, 10.5, 11.0]),
        highs=np.array([10.5, 11.0, 11.5]),
        lows=np.array([9.5, 10.0, 10.5]),
        closes=np.array([10.2, 10.8, 11.2]),
        volumes=np.array([1000.0, 2000.0, 1500.0]),
    )


@pytest.fixture
def bar_data_from_dicts():
    """从字典创建BarData"""
    bars = [
        {"open": 10.0, "high": 10.5, "low": 9.5, "close": 10.2, "volume": 1000},
        {"open": 10.2, "high": 11.0, "low": 10.0, "close": 10.8, "volume": 2000},
        {"open": 10.8, "high": 11.5, "low": 10.5, "close": 11.2, "volume": 1500},
        {"open": 11.2, "high": 11.8, "low": 11.0, "close": 11.5, "volume": 3000},
        {"open": 11.5, "high": 12.0, "low": 11.2, "close": 11.8, "volume": 2500},
    ]
    return BarData.from_dicts(bars)


# ============ BarData Tests ============

class TestBarData:
    def test_from_dicts(self, bar_data_from_dicts):
        assert len(bar_data_from_dicts) == 5
        assert bar_data_from_dicts.closes[0] == 10.2
        assert bar_data_from_dicts.volumes[1] == 2000

    def test_from_dicts_empty(self):
        data = BarData.from_dicts([])
        assert len(data) == 0

    def test_from_dicts_no_amount(self):
        bars = [{"open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000}]
        data = BarData.from_dicts(bars)
        assert data.amounts is None


# ============ Trend Indicator Tests ============

class TestSMA:
    def test_calculate(self, sample_bars):
        sma = SMA(periods=[5, 10])
        result = sma.calculate(sample_bars)
        assert "sma5" in result.values
        assert "sma10" in result.values
        assert len(result.values["sma5"]) == len(sample_bars)
        # SMA(5) from index 4 onward should be valid
        assert result.values["sma5"][4] != 0

    def test_short_data(self, short_bars):
        sma = SMA(periods=[60])
        result = sma.calculate(short_bars)
        assert len(result.values["sma60"]) == 3
        assert all(v == 0 for v in result.values["sma60"])

    def test_params(self):
        sma = SMA(periods=[7, 14])
        assert sma.periods == [7, 14]


class TestEMA:
    def test_calculate(self, sample_bars):
        ema = EMA(periods=[12])
        result = ema.calculate(sample_bars)
        assert "ema12" in result.values
        assert len(result.values["ema12"]) == len(sample_bars)

    def test_short_data(self, short_bars):
        ema = EMA(periods=[20])
        result = ema.calculate(short_bars)
        assert len(result.values["ema20"]) == 3


class TestMACD:
    def test_calculate(self, sample_bars):
        macd = MACD()
        result = macd.calculate(sample_bars)
        assert "dif" in result.values
        assert "dea" in result.values
        assert "macd_bar" in result.values
        assert len(result.values["dif"]) == len(sample_bars)

    def test_short_data(self, short_bars):
        macd = MACD()
        result = macd.calculate(short_bars)
        assert len(result.values["dif"]) == 3

    def test_params(self):
        macd = MACD(fast=8, slow=21, signal=5)
        assert macd.fast == 8
        assert macd.slow == 21


class TestBOLL:
    def test_calculate(self, sample_bars):
        boll = BOLL()
        result = boll.calculate(sample_bars)
        assert "upper" in result.values
        assert "middle" in result.values
        assert "lower" in result.values
        # Upper > Middle > Lower for valid data
        idx = 25  # index where all values should be valid
        if not np.isnan(result.values["upper"][idx]):
            assert result.values["upper"][idx] >= result.values["middle"][idx]
            assert result.values["lower"][idx] <= result.values["middle"][idx]


class TestTRIX:
    def test_calculate(self, sample_bars):
        trix = TRIX(period=12)
        result = trix.calculate(sample_bars)
        assert "trix" in result.values
        assert "ma_trix" in result.values

    def test_short_data(self, short_bars):
        trix = TRIX()
        result = trix.calculate(short_bars)
        assert len(result.values["trix"]) == 3


class TestDEMA:
    def test_calculate(self, sample_bars):
        dema = DEMA(period=20)
        result = dema.calculate(sample_bars)
        assert "dema" in result.values
        assert len(result.values["dema"]) == len(sample_bars)


# ============ Oscillator Tests ============

class TestKDJ:
    def test_calculate(self, sample_bars):
        kdj = KDJ()
        result = kdj.calculate(sample_bars)
        assert "k" in result.values
        assert "d" in result.values
        assert "j" in result.values
        # K, D should be between 0-100 typically
        k_vals = result.values["k"]
        d_vals = result.values["d"]
        assert all(0 <= v <= 100 for v in k_vals)
        assert all(0 <= v <= 100 for v in d_vals)

    def test_short_data(self, short_bars):
        kdj = KDJ()
        result = kdj.calculate(short_bars)
        assert len(result.values["k"]) == 3


class TestRSI:
    def test_calculate(self, sample_bars):
        rsi = RSI(periods=[6, 14])
        result = rsi.calculate(sample_bars)
        assert "rsi6" in result.values
        assert "rsi14" in result.values
        # RSI should be 0-100
        rsi14 = result.values["rsi14"]
        assert all(0 <= v <= 100 for v in rsi14)

    def test_short_data(self, short_bars):
        rsi = RSI()
        result = rsi.calculate(short_bars)
        assert len(result.values["rsi6"]) == 3


class TestCCI:
    def test_calculate(self, sample_bars):
        cci = CCI()
        result = cci.calculate(sample_bars)
        assert "cci" in result.values
        assert len(result.values["cci"]) == len(sample_bars)


class TestWR:
    def test_calculate(self, sample_bars):
        wr = WR()
        result = wr.calculate(sample_bars)
        assert "wr" in result.values
        # WR should be -100 to 0
        wr_vals = result.values["wr"]
        assert all(-100 <= v <= 0 for v in wr_vals)


class TestROC:
    def test_calculate(self, sample_bars):
        roc = ROC()
        result = roc.calculate(sample_bars)
        assert "roc" in result.values

    def test_short_data(self, short_bars):
        roc = ROC()
        result = roc.calculate(short_bars)
        assert len(result.values["roc"]) == 3


# ============ Volume Indicator Tests ============

class TestOBV:
    def test_calculate(self, sample_bars):
        obv = OBV()
        result = obv.calculate(sample_bars)
        assert "obv" in result.values

    def test_rising_prices(self):
        """上涨时OBV应该增加"""
        data = BarData(
            opens=np.array([10, 11, 12], dtype=np.float64),
            highs=np.array([11, 12, 13], dtype=np.float64),
            lows=np.array([9, 10, 11], dtype=np.float64),
            closes=np.array([10.5, 11.5, 12.5], dtype=np.float64),
            volumes=np.array([1000, 1000, 1000], dtype=np.float64),
        )
        result = OBV().calculate(data)
        obv = result.values["obv"]
        assert obv[2] > obv[0]


class TestVR:
    def test_calculate(self, sample_bars):
        vr = VR()
        result = vr.calculate(sample_bars)
        assert "vr" in result.values


class TestEMV:
    def test_calculate(self, sample_bars):
        emv = EMV()
        result = emv.calculate(sample_bars)
        assert "emv" in result.values
        assert "ma_emv" in result.values


# ============ Volatility Indicator Tests ============

class TestATR:
    def test_calculate(self, sample_bars):
        atr = ATR()
        result = atr.calculate(sample_bars)
        assert "atr" in result.values
        # ATR should be non-negative
        atr_vals = result.values["atr"]
        assert all(v >= 0 for v in atr_vals)

    def test_short_data(self, short_bars):
        atr = ATR()
        result = atr.calculate(short_bars)
        assert len(result.values["atr"]) == 3


class TestSAR:
    def test_calculate(self, sample_bars):
        sar = SAR()
        result = sar.calculate(sample_bars)
        assert "sar" in result.values
        assert len(result.values["sar"]) == len(sample_bars)


# ============ Calculator Tests ============

class TestIndicatorCalculator:
    def test_list_indicators(self):
        indicators = IndicatorCalculator.list_indicators()
        assert len(indicators) > 0
        names = [i["name"] for i in indicators]
        assert "SMA" in names
        assert "MACD" in names
        assert "KDJ" in names

    def test_calculate_all(self, sample_bars):
        calc = IndicatorCalculator()
        results = calc.calculate_all_default(sample_bars)
        assert len(results) >= 16
        assert "SMA" in results
        assert "MACD" in results

    def test_calculate_specific(self, sample_bars):
        calc = IndicatorCalculator()
        results = calc.calculate(sample_bars, ["SMA", "MACD"])
        assert "SMA" in results
        assert "MACD" in results
        assert "KDJ" not in results

    def test_calculate_unknown(self, sample_bars):
        calc = IndicatorCalculator()
        results = calc.calculate(sample_bars, ["UNKNOWN"])
        assert "UNKNOWN" not in results

    def test_create_from_config(self, sample_bars):
        config = {
            "SMA": {"periods": [7, 14]},
            "MACD": {"fast": 8, "slow": 21, "signal": 5},
        }
        calc = IndicatorCalculator.create_from_config(config)
        results = calc.calculate(sample_bars, ["SMA", "MACD"])
        assert "SMA" in results
        assert "sma7" in results["SMA"].values


# ============ IndicatorResult Tests ============

class TestIndicatorResult:
    def test_to_dict(self):
        result = IndicatorResult(
            name="TEST",
            values={"val": [1.0, 2.0, 3.0]},
            params={"period": 10},
        )
        d = result.to_dict()
        assert d["name"] == "TEST"
        assert d["params"]["period"] == 10
        assert d["values"]["val"] == [1.0, 2.0, 3.0]

    def test_latest(self):
        result = IndicatorResult(
            name="TEST",
            values={"val": [1.0, 2.0, 3.0]},
        )
        latest = result.latest()
        assert latest["val"] == 3.0

    def test_latest_empty(self):
        result = IndicatorResult(name="TEST", values={"val": []})
        latest = result.latest()
        assert latest["val"] is None
