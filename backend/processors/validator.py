# -*- coding: utf-8 -*-
"""
数据验证模块

验证数据的完整性、准确性和一致性
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from pydantic import ValidationError


class DataValidator:
    """
    数据验证器

    提供多种数据验证规则
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化验证器

        Args:
            config: 配置字典
        """
        self.config = config or {}

        # 验证规则配置
        self.strict_mode = self.config.get("strict_mode", False)
        self.validate_price_logic = self.config.get("validate_price_logic", True)
        self.validate_volume = self.config.get("validate_volume", True)
        self.validate_timestamp = self.config.get("validate_timestamp", True)

        # 价格范围限制
        self.min_price = self.config.get("min_price", 0.01)
        self.max_price = self.config.get("max_price", 100000)

        # 涨跌幅限制
        self.max_change_percent = self.config.get("max_change_percent", 20.0)

        # 统计
        self.stats = {
            "total_validated": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "errors": [],
        }

    def validate_quote(self, quote: Dict) -> Tuple[bool, List[str]]:
        """
        验证行情数据

        Args:
            quote: 行情数据字典

        Returns:
            (是否有效, 错误信息列表)
        """
        self.stats["total_validated"] += 1
        errors = []

        # 1. 必填字段检查
        required_fields = ["symbol", "ts"]
        for field in required_fields:
            if field not in quote or quote[field] is None:
                errors.append(f"Missing required field: {field}")

        # 2. 价格验证
        if self.validate_price_logic:
            price_errors = self._validate_prices(quote)
            errors.extend(price_errors)

        # 3. 成交量验证
        if self.validate_volume:
            volume_errors = self._validate_volume(quote)
            errors.extend(volume_errors)

        # 4. 时间戳验证
        if self.validate_timestamp:
            timestamp_errors = self._validate_timestamp(quote)
            errors.extend(timestamp_errors)

        # 5. 涨跌幅验证
        change_errors = self._validate_change(quote)
        errors.extend(change_errors)

        # 更新统计
        is_valid = len(errors) == 0
        if is_valid:
            self.stats["valid_count"] += 1
        else:
            self.stats["invalid_count"] += 1
            if self.strict_mode:
                self.stats["errors"].append({
                    "symbol": quote.get("symbol"),
                    "errors": errors,
                })

        return is_valid, errors

    def validate_bar(self, bar: Dict) -> Tuple[bool, List[str]]:
        """
        验证K线数据

        Args:
            bar: K线数据字典

        Returns:
            (是否有效, 错误信息列表)
        """
        self.stats["total_validated"] += 1
        errors = []

        # 1. 必填字段检查
        required_fields = ["symbol", "interval", "ts", "open", "high", "low", "close", "volume"]
        for field in required_fields:
            if field not in bar or bar[field] is None:
                errors.append(f"Missing required field: {field}")

        # 2. K线逻辑验证
        if all(k in bar for k in ["open", "high", "low", "close"]):
            if bar["high"] < bar["open"] or bar["high"] < bar["close"]:
                errors.append("high must be >= open and close")

            if bar["low"] > bar["open"] or bar["low"] > bar["close"]:
                errors.append("low must be <= open and close")

            if bar["high"] < bar["low"]:
                errors.append("high must be >= low")

        # 3. 价格范围验证
        for field in ["open", "high", "low", "close"]:
            if field in bar and bar[field] is not None:
                price = bar[field]
                if price < self.min_price or price > self.max_price:
                    errors.append(f"{field} price {price} out of range")

        # 4. 成交量验证
        if "volume" in bar and bar["volume"] is not None:
            if bar["volume"] < 0:
                errors.append("volume cannot be negative")

        # 更新统计
        is_valid = len(errors) == 0
        if is_valid:
            self.stats["valid_count"] += 1
        else:
            self.stats["invalid_count"] += 1

        return is_valid, errors

    def _validate_prices(self, quote: Dict) -> List[str]:
        """验证价格数据"""
        errors = []

        price_fields = ["open", "high", "low", "close", "pre_close"]

        # 检查价格范围
        for field in price_fields:
            if field in quote and quote[field] is not None:
                price = quote[field]
                if price < self.min_price or price > self.max_price:
                    errors.append(f"{field} price {price} out of range [{self.min_price}, {self.max_price}]")

        # 检查价格逻辑
        if all(f in quote for f in ["open", "high", "low", "close"]):
            if quote["high"] < quote["open"] or quote["high"] < quote["close"]:
                errors.append("high must be >= open and close")

            if quote["low"] > quote["open"] or quote["low"] > quote["close"]:
                errors.append("low must be <= open and close")

        return errors

    def _validate_volume(self, quote: Dict) -> List[str]:
        """验证成交量"""
        errors = []

        # 成交量不能为负
        if "volume" in quote and quote["volume"] is not None:
            if quote["volume"] < 0:
                errors.append("volume cannot be negative")

        # 成交额不能为负
        if "amount" in quote and quote["amount"] is not None:
            if quote["amount"] < 0:
                errors.append("amount cannot be negative")

        # 如果有成交量和成交额，计算均价应该合理
        if ("volume" in quote and quote["volume"] and quote["volume"] > 0 and
            "amount" in quote and quote["amount"] and quote["amount"] > 0):
            avg_price = quote["amount"] / quote["volume"]
            if avg_price < self.min_price or avg_price > self.max_price:
                errors.append(f"calculated avg price {avg_price} out of range")

        return errors

    def _validate_timestamp(self, quote: Dict) -> List[str]:
        """验证时间戳"""
        errors = []

        if "ts" not in quote or quote["ts"] is None:
            return errors

        ts = quote["ts"]

        # 转换为datetime对象
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"invalid timestamp format: {ts}")
                return errors

        # 检查时间范围（不能是未来时间，不能太久以前）
        now = datetime.now()
        if ts > now + timedelta(minutes=5):
            errors.append(f"timestamp is in the future: {ts}")

        if ts < now - timedelta(days=30):
            errors.append(f"timestamp is too old: {ts}")

        return errors

    def _validate_change(self, quote: Dict) -> List[str]:
        """验证涨跌幅"""
        errors = []

        # 如果有涨跌幅数据，检查是否合理
        if "change_percent" in quote and quote["change_percent"] is not None:
            change_pct = abs(quote["change_percent"])
            if change_pct > self.max_change_percent:
                errors.append(f"change_percent {quote['change_percent']} exceeds limit {self.max_change_percent}%")

        # 验证涨跌幅计算是否正确
        if all(k in quote for k in ["close", "pre_close", "change_percent"]):
            expected_change = (quote["close"] - quote["pre_close"]) / quote["pre_close"] * 100
            actual_change = quote["change_percent"]
            if abs(expected_change - actual_change) > 0.1:
                errors.append(f"change_percent mismatch: expected {expected_change:.2f}%, got {actual_change:.2f}%")

        return errors

    def validate_batch(self, data: List[Dict], data_type: str = "quote") -> Tuple[List[Dict], List[Dict]]:
        """
        批量验证数据

        Args:
            data: 数据列表
            data_type: 数据类型 (quote/bar)

        Returns:
            (有效数据列表, 无效数据列表)
        """
        valid_data = []
        invalid_data = []

        for item in data:
            if data_type == "bar":
                is_valid, errors = self.validate_bar(item)
            else:
                is_valid, errors = self.validate_quote(item)

            if is_valid:
                valid_data.append(item)
            else:
                invalid_data.append({
                    "data": item,
                    "errors": errors,
                })

        logger.info(f"Validated {len(data)} items: {len(valid_data)} valid, {len(invalid_data)} invalid")

        return valid_data, invalid_data

    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        stats = self.stats.copy()
        if stats["total_validated"] > 0:
            stats["valid_rate"] = stats["valid_count"] / stats["total_validated"]
        else:
            stats["valid_rate"] = 0
        return stats

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_validated": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "errors": [],
        }
