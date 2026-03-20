# -*- coding: utf-8 -*-
"""
数据清洗模块

处理原始数据中的重复、缺失、异常等问题
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np


class DataCleaner:
    """
    数据清洗器

    提供多种数据清洗功能
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化清洗器

        Args:
            config: 配置字典
        """
        self.config = config or {}

        # 清洗规则配置
        self.remove_duplicates = self.config.get("remove_duplicates", True)
        self.fill_missing = self.config.get("fill_missing", True)
        self.fill_method = self.config.get("fill_method", "forward")  # forward/backward/mean
        self.detect_outliers = self.config.get("detect_outliers", True)
        self.outlier_method = self.config.get("outlier_method", "zscore")  # zscore/iqr
        self.outlier_threshold = self.config.get("outlier_threshold", 3.0)

        # 统计
        self.stats = {
            "total_processed": 0,
            "duplicates_removed": 0,
            "missing_filled": 0,
            "outliers_handled": 0,
        }

    async def clean_quotes(self, quotes: List[Dict]) -> List[Dict]:
        """
        清洗行情数据

        Args:
            quotes: 原始行情数据列表

        Returns:
            清洗后的数据列表
        """
        if not quotes:
            return []

        self.stats["total_processed"] += len(quotes)

        # 转换为DataFrame
        df = pd.DataFrame(quotes)

        # 1. 去重
        if self.remove_duplicates:
            original_count = len(df)
            df = self._remove_duplicates(df)
            removed = original_count - len(df)
            self.stats["duplicates_removed"] += removed
            if removed > 0:
                logger.debug(f"Removed {removed} duplicate quotes")

        # 2. 处理缺失值
        if self.fill_missing:
            filled = self._fill_missing(df)
            self.stats["missing_filled"] += filled
            if filled > 0:
                logger.debug(f"Filled {filled} missing values")

        # 3. 检测和处理异常值
        if self.detect_outliers:
            handled = self._handle_outliers(df)
            self.stats["outliers_handled"] += handled
            if handled > 0:
                logger.debug(f"Handled {handled} outliers")

        # 4. 数据类型转换和标准化
        df = self._standardize_types(df)

        # 转回列表
        cleaned = df.to_dict("records")

        logger.debug(f"Cleaned {len(quotes)} quotes -> {len(cleaned)}")
        return cleaned

    async def clean_bars(self, bars: List[Dict]) -> List[Dict]:
        """
        清洗K线数据

        Args:
            bars: 原始K线数据列表

        Returns:
            清洗后的数据列表
        """
        if not bars:
            return []

        self.stats["total_processed"] += len(bars)

        df = pd.DataFrame(bars)

        # 1. 去重
        if self.remove_duplicates:
            original_count = len(df)
            df = self._remove_duplicates(df)
            self.stats["duplicates_removed"] += original_count - len(df)

        # 2. 处理缺失值
        if self.fill_missing:
            self._fill_missing(df)

        # 3. K线特殊处理
        df = self._validate_bars(df)

        # 4. 异常值处理
        if self.detect_outliers:
            self._handle_outliers(df)

        return df.to_dict("records")

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        去除重复数据

        基于symbol和ts进行去重，保留最后一条
        """
        if "symbol" in df.columns and "ts" in df.columns:
            return df.drop_duplicates(subset=["symbol", "ts"], keep="last")
        return df

    def _fill_missing(self, df: pd.DataFrame) -> int:
        """
        填充缺失值

        Returns:
            填充的值数量
        """
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        filled_count = 0

        if self.fill_method == "forward":
            # 前向填充
            for col in numeric_columns:
                missing = df[col].isna().sum()
                if missing > 0:
                    df[col] = df[col].ffill()
                    filled_count += int(missing)

        elif self.fill_method == "backward":
            # 后向填充
            for col in numeric_columns:
                missing = df[col].isna().sum()
                if missing > 0:
                    df[col] = df[col].bfill()
                    filled_count += int(missing)

        elif self.fill_method == "mean":
            # 均值填充
            for col in numeric_columns:
                missing = df[col].isna().sum()
                if missing > 0:
                    mean_value = df[col].mean()
                    df[col] = df[col].fillna(mean_value)
                    filled_count += missing

        return filled_count

    def _handle_outliers(self, df: pd.DataFrame) -> int:
        """
        处理异常值

        Returns:
            处理的异常值数量
        """
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        handled_count = 0

        for col in numeric_columns:
            if col not in ["open", "high", "low", "close", "volume", "amount"]:
                continue

            if self.outlier_method == "zscore":
                # Z-score方法
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    z_scores = np.abs((df[col] - mean) / std)
                    outliers = z_scores > self.outlier_threshold
                    handled_count += outliers.sum()
                    # 用中位数替换异常值
                    df.loc[outliers, col] = df[col].median()

            elif self.outlier_method == "iqr":
                # IQR方法
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.outlier_threshold * IQR
                upper_bound = Q3 + self.outlier_threshold * IQR
                outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
                handled_count += outliers.sum()
                df.loc[outliers, col] = df[col].median()

        return handled_count

    def _validate_bars(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证K线数据的逻辑性

        - high >= max(open, close)
        - low <= min(open, close)
        - volume >= 0
        """
        required_cols = ["open", "high", "low", "close"]
        if not all(col in df.columns for col in required_cols):
            return df

        # 检查价格逻辑
        invalid_high = df["high"] < df[["open", "close"]].max(axis=1)
        invalid_low = df["low"] > df[["open", "close"]].min(axis=1)

        # 修正无效数据
        df.loc[invalid_high, "high"] = df[invalid_high][["open", "close"]].max(axis=1)
        df.loc[invalid_low, "low"] = df[invalid_low][["open", "close"]].min(axis=1)

        # 确保成交量为非负
        if "volume" in df.columns:
            df.loc[df["volume"] < 0, "volume"] = 0

        return df

    def _standardize_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化数据类型

        - 时间戳统一为datetime
        - 价格统一为float
        - 成交量统一为float
        """
        # 时间戳处理
        if "ts" in df.columns:
            df["ts"] = pd.to_datetime(df["ts"])

        # 数值类型处理
        numeric_cols = ["open", "high", "low", "close", "volume", "amount",
                       "pre_close", "change", "change_percent"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def get_stats(self) -> Dict[str, Any]:
        """获取清洗统计信息"""
        return self.stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "duplicates_removed": 0,
            "missing_filled": 0,
            "outliers_handled": 0,
        }


class StreamingDataCleaner:
    """
    流式数据清洗器

    适用于实时数据流的清洗
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.cleaner = DataCleaner(config)

        # 去重缓存（保留最近的数据用于去重）
        self._dedup_cache: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(seconds=5)

    async def clean_stream(self, data: Dict) -> Optional[Dict]:
        """
        清洗单条流式数据

        Args:
            data: 原始数据

        Returns:
            清洗后的数据，如果数据无效则返回None
        """
        # 1. 去重检查
        if self._is_duplicate(data):
            return None

        # 2. 基本验证
        if not self._validate_basic(data):
            return None

        # 3. 数据清洗
        cleaned = self._clean_single(data)

        # 4. 更新去重缓存
        self._update_dedup_cache(cleaned)

        return cleaned

    def _is_duplicate(self, data: Dict) -> bool:
        """检查是否重复"""
        symbol = data.get("symbol", "")
        ts = data.get("ts")

        if not symbol or not ts:
            return False

        key = f"{symbol}_{ts}"
        last_ts = self._dedup_cache.get(key)

        if last_ts:
            return datetime.now() - last_ts < self._cache_ttl

        return False

    def _update_dedup_cache(self, data: Dict):
        """更新去重缓存"""
        symbol = data.get("symbol", "")
        ts = data.get("ts")

        if symbol and ts:
            key = f"{symbol}_{ts}"
            self._dedup_cache[key] = datetime.now()

            # 清理过期缓存
            now = datetime.now()
            expired = [k for k, v in self._dedup_cache.items()
                      if now - v > self._cache_ttl]
            for k in expired:
                del self._dedup_cache[k]

    def _validate_basic(self, data: Dict) -> bool:
        """基本数据验证"""
        # 必须有symbol
        if not data.get("symbol"):
            return False

        # 价格必须为正数
        price_fields = ["open", "high", "low", "close"]
        for field in price_fields:
            value = data.get(field)
            if value is not None:
                try:
                    # 尝试转换为float进行比较
                    if float(value) <= 0:
                        return False
                except (ValueError, TypeError):
                    return False

        # 成交量不能为负
        volume = data.get("volume")
        if volume is not None:
            try:
                if float(volume) < 0:
                    return False
            except (ValueError, TypeError):
                return False

        return True

    def _clean_single(self, data: Dict) -> Dict:
        """清洗单条数据"""
        cleaned = data.copy()

        # 价格逻辑修正
        if all(k in cleaned for k in ["open", "high", "low", "close"]):
            high = max(cleaned["open"], cleaned["close"])
            low = min(cleaned["open"], cleaned["close"])

            if cleaned["high"] < high:
                cleaned["high"] = high
            if cleaned["low"] > low:
                cleaned["low"] = low

        # 确保数值类型
        numeric_fields = ["open", "high", "low", "close", "volume", "amount",
                         "pre_close", "change", "change_percent"]
        for field in numeric_fields:
            if field in cleaned and cleaned[field] is not None:
                try:
                    cleaned[field] = float(cleaned[field])
                except (ValueError, TypeError):
                    cleaned[field] = None

        return cleaned
