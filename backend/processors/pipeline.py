# -*- coding: utf-8 -*-
"""
数据管道模块

连接数据采集、清洗、验证和存储的完整数据管道
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from .cleaner import DataCleaner
from .validator import DataValidator
from .incremental import IncrementalProcessor


class DataPipeline:
    """
    数据管道

    将采集的原始数据通过清洗→验证→增量处理→存储的完整流程
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 初始化处理器
        self.cleaner = DataCleaner(self.config.get("cleaner", {}))
        self.validator = DataValidator(self.config.get("validator", {}))
        self.incremental = IncrementalProcessor(self.config.get("incremental", {}))

        # 统计
        self.stats = {
            "total_input": 0,
            "cleaned": 0,
            "validated": 0,
            "stored": 0,
            "dropped": 0,
            "errors": 0,
        }

    async def process_quotes(
        self,
        quotes: List[Any],
        data_type: str = "stock",
        store_fn=None,
    ) -> Dict[str, int]:
        """
        处理行情数据（清洗→验证→存储）

        Args:
            quotes: 原始行情数据列表
            data_type: 数据类型 (stock/futures/index)
            store_fn: 存储函数 async Callable[[Dict], bool]

        Returns:
            处理统计
        """
        if not quotes:
            return {"input": 0, "stored": 0, "dropped": 0}

        result = {"input": len(quotes), "stored": 0, "dropped": 0}
        self.stats["total_input"] += len(quotes)

        # 转换为字典列表
        raw_data = []
        for q in quotes:
            if hasattr(q, "model_dump"):
                raw_data.append(q.model_dump())
            elif hasattr(q, "__dict__"):
                raw_data.append(q.__dict__)
            elif isinstance(q, dict):
                raw_data.append(q)
            else:
                raw_data.append({"data": q})

        # 1. 数据清洗
        try:
            cleaned = await self.cleaner.clean_quotes(raw_data)
            self.stats["cleaned"] += len(cleaned)
        except Exception as e:
            logger.error(f"数据清洗失败: {e}")
            cleaned = raw_data  # 清洗失败用原始数据继续
            self.stats["errors"] += 1

        # 2. 数据验证
        valid_data = []
        for item in cleaned:
            try:
                is_valid, errors = self.validator.validate_quote(item)
                if is_valid:
                    valid_data.append(item)
                else:
                    result["dropped"] += 1
                    logger.debug(f"数据验证失败: {errors}")
            except Exception as e:
                logger.debug(f"验证异常: {e}")
                result["dropped"] += 1

        self.stats["validated"] += len(valid_data)

        # 3. 存储
        if store_fn:
            for item in valid_data:
                try:
                    success = await store_fn(item)
                    if success:
                        result["stored"] += 1
                        self.stats["stored"] += 1
                    else:
                        result["dropped"] += 1
                        self.stats["dropped"] += 1
                except Exception as e:
                    logger.error(f"存储失败: {e}")
                    result["dropped"] += 1
                    self.stats["errors"] += 1
        else:
            result["stored"] = len(valid_data)

        return result

    def get_stats(self) -> Dict:
        """获取管道统计"""
        return {
            "pipeline": self.stats.copy(),
            "cleaner": self.cleaner.stats,
            "validator": self.validator.stats,
        }


# 全局实例
_pipeline: Optional[DataPipeline] = None


def get_data_pipeline(config: Optional[Dict] = None) -> DataPipeline:
    """获取全局数据管道实例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = DataPipeline(config)
    return _pipeline
