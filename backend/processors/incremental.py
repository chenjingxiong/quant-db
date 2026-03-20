# -*- coding: utf-8 -*-
"""
增量数据处理模块

处理增量数据的获取、合并和存储
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd


class IncrementalProcessor:
    """
    增量数据处理器

    管理增量数据的获取、去重和合并
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化增量处理器

        Args:
            config: 配置字典
        """
        self.config = config or {}

        # 缓存最新数据时间戳
        self._latest_timestamps: Dict[str, datetime] = {}

        # 缓存最新数据（用于合并）
        self._latest_data: Dict[str, Dict] = {}

    async def get_increment_range(
        self,
        symbol: str,
        data_type: str,
        interval: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取增量数据的时间范围

        Args:
            symbol: 标的代码
            data_type: 数据类型
            interval: 周期

        Returns:
            (开始时间, 结束时间)
        """
        key = f"{symbol}_{data_type}_{interval}"

        # 获取上次更新的时间戳
        last_ts = self._latest_timestamps.get(key)

        if last_ts:
            # 从上次时间戳到现在
            start_time = last_ts
            end_time = datetime.now()
        else:
            # 首次获取，返回None表示需要获取历史数据
            start_time = None
            end_time = None

        return start_time, end_time

    async def merge_with_existing(
        self,
        new_data: List[Dict],
        symbol: str,
        data_type: str,
        interval: str
    ) -> List[Dict]:
        """
        将新数据与已有数据合并

        Args:
            new_data: 新数据列表
            symbol: 标的代码
            data_type: 数据类型
            interval: 周期

        Returns:
            合并后的数据列表
        """
        if not new_data:
            return []

        key = f"{symbol}_{data_type}_{interval}"

        # 转换为DataFrame
        df_new = pd.DataFrame(new_data)
        df_new["ts"] = pd.to_datetime(df_new["ts"])

        # 获取已有数据
        existing_data = self._latest_data.get(key, [])
        if existing_data:
            df_existing = pd.DataFrame(existing_data)
            df_existing["ts"] = pd.to_datetime(df_existing["ts"])

            # 合并并去重（保留新数据）
            df_merged = pd.concat([df_existing, df_new], ignore_index=True)
            df_merged = df_merged.drop_duplicates(subset=["ts"], keep="last")
            df_merged = df_merged.sort_values("ts").reset_index(drop=True)
        else:
            df_merged = df_new.sort_values("ts").reset_index(drop=True)

        # 更新缓存
        merged_data = df_merged.to_dict("records")
        self._latest_data[key] = merged_data

        # 更新最新时间戳
        if not df_merged.empty:
            self._latest_timestamps[key] = df_merged["ts"].max()

        return merged_data

    def update_latest_timestamp(self, symbol: str, data_type: str, interval: str, ts: datetime):
        """
        更新最新时间戳

        Args:
            symbol: 标的代码
            data_type: 数据类型
            interval: 周期
            ts: 时间戳
        """
        key = f"{symbol}_{data_type}_{interval}"

        current = self._latest_timestamps.get(key)
        if current is None or ts > current:
            self._latest_timestamps[key] = ts
            logger.debug(f"Updated latest timestamp for {key}: {ts}")

    def get_latest_timestamp(self, symbol: str, data_type: str, interval: str) -> Optional[datetime]:
        """
        获取最新时间戳

        Args:
            symbol: 标的代码
            data_type: 数据类型
            interval: 周期

        Returns:
            最新时间戳
        """
        key = f"{symbol}_{data_type}_{interval}"
        return self._latest_timestamps.get(key)

    def clear_cache(self, symbol: Optional[str] = None):
        """
        清除缓存

        Args:
            symbol: 如果指定，只清除该标的的缓存；否则清除所有
        """
        if symbol:
            keys_to_remove = [k for k in self._latest_timestamps if k.startswith(symbol)]
            for key in keys_to_remove:
                del self._latest_timestamps[key]
                del self._latest_data[key]
            logger.info(f"Cleared cache for {symbol}")
        else:
            self._latest_timestamps.clear()
            self._latest_data.clear()
            logger.info("Cleared all cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cached_symbols": len(self._latest_timestamps),
            "cache_keys": list(self._latest_timestamps.keys()),
        }


class IncrementalCollector:
    """
    增量数据采集器

    基于时间戳进行增量数据采集
    """

    def __init__(
        self,
        adapter,
        processor: IncrementalProcessor,
        config: Optional[Dict] = None
    ):
        """
        初始化增量采集器

        Args:
            adapter: 数据源适配器
            processor: 增量处理器
            config: 配置字典
        """
        self.adapter = adapter
        self.processor = processor
        self.config = config or {}

        # 采集配置
        self.batch_size = self.config.get("batch_size", 1000)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5)

    async def collect_incremental_bars(
        self,
        symbol: str,
        interval: str,
        data_type: str = "stock"
    ) -> List[Dict]:
        """
        增量采集K线数据

        Args:
            symbol: 标的代码
            interval: K线周期
            data_type: 数据类型

        Returns:
            K线数据列表
        """
        # 获取增量范围
        start_time, end_time = await self.processor.get_increment_range(
            symbol, data_type, interval
        )

        # 获取数据
        if data_type == "stock":
            bars = await self.adapter.get_stock_bars(
                symbol, interval, start_time, end_time, self.batch_size
            )
        else:
            bars = await self.adapter.get_futures_bars(
                symbol, interval, start_time, end_time, self.batch_size
            )

        if not bars:
            logger.debug(f"No new bars for {symbol} {interval}")
            return []

        # 合并数据
        merged = await self.processor.merge_with_existing(
            bars, symbol, data_type, interval
        )

        logger.info(f"Collected {len(bars)} new bars, merged to {len(merged)} total")

        return merged

    async def collect_incremental_quotes(
        self,
        symbols: List[str],
        data_type: str = "stock"
    ) -> List[Dict]:
        """
        增量采集行情数据

        Args:
            symbols: 标的代码列表
            data_type: 数据类型

        Returns:
            行情数据列表
        """
        # 获取行情数据
        if data_type == "stock":
            quotes = await self.adapter.get_stock_quotes(symbols)
        elif data_type == "futures":
            quotes = await self.adapter.get_futures_quotes(symbols)
        elif data_type == "index":
            quotes = await self.adapter.get_index_quotes(symbols)
        else:
            logger.warning(f"Unknown data type: {data_type}")
            return []

        if not quotes:
            logger.debug(f"No new quotes for {symbols}")
            return []

        # 更新时间戳
        for quote in quotes:
            if "ts" in quote:
                self.processor.update_latest_timestamp(
                    quote["symbol"], data_type, "tick", quote["ts"]
                )

        return quotes

    async def sync_historical_bars(
        self,
        symbol: str,
        interval: str,
        days: int = 30,
        data_type: str = "stock"
    ) -> List[Dict]:
        """
        同步历史K线数据

        Args:
            symbol: 标的代码
            interval: K线周期
            days: 天数
            data_type: 数据类型

        Returns:
            K线数据列表
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        if data_type == "stock":
            bars = await self.adapter.get_stock_bars(
                symbol, interval, start_time, end_time, self.batch_size
            )
        else:
            bars = await self.adapter.get_futures_bars(
                symbol, interval, start_time, end_time, self.batch_size
            )

        # 合并数据
        merged = await self.processor.merge_with_existing(
            bars, symbol, data_type, interval
        )

        logger.info(f"Synced {len(bars)} historical bars for {symbol} {interval}")

        return merged
