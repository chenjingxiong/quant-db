# -*- coding: utf-8 -*-
"""
性能分析器

提供函数级性能分析和统计
"""
import time
import functools
from typing import Callable, Optional, Dict, Any, List
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime
from loguru import logger
import asyncio


class Profiler:
    """性能分析器"""

    def __init__(self):
        self.stats: Dict[str, Dict] = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "errors": 0,
        })
        self._call_stack: List[str] = []
        self._start_times: Dict[str, float] = {}

    @contextmanager
    def profile(self, name: str):
        """
        上下文管理器性能分析

        Args:
            name: 分析名称

        使用示例:
            with profiler.profile("database_query"):
                result = db.execute(query)
        """
        self._call_stack.append(name)
        start_time = time.perf_counter()
        self._start_times[name] = start_time

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            self._record_stats(name, elapsed, success=True)
            self._call_stack.pop()
            if name in self._start_times:
                del self._start_times[name]

    def record(self, name: str, duration: float, success: bool = True):
        """
        手动记录性能数据

        Args:
            name: 操作名称
            duration: 耗时（秒）
            success: 是否成功
        """
        self._record_stats(name, duration, success)

    def _record_stats(self, name: str, duration: float, success: bool):
        """记录统计数据"""
        stats = self.stats[name]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        if not success:
            stats["errors"] += 1

    def get_stats(self, name: Optional[str] = None) -> Dict:
        """
        获取性能统计

        Args:
            name: 操作名称，None表示获取所有

        Returns:
            统计数据字典
        """
        if name:
            stats = self.stats.get(name, {})
            if stats and stats["count"] > 0:
                return {
                    "name": name,
                    "count": stats["count"],
                    "total_time": stats["total_time"],
                    "avg_time": stats["total_time"] / stats["count"],
                    "min_time": stats["min_time"],
                    "max_time": stats["max_time"],
                    "error_rate": stats["errors"] / stats["count"],
                }
            return {}
        else:
            result = []
            for name, stats in self.stats.items():
                if stats["count"] > 0:
                    result.append({
                        "name": name,
                        "count": stats["count"],
                        "total_time": stats["total_time"],
                        "avg_time": stats["total_time"] / stats["count"],
                        "min_time": stats["min_time"],
                        "max_time": stats["max_time"],
                        "error_rate": stats["errors"] / stats["count"],
                    })
            return sorted(result, key=lambda x: x["total_time"], reverse=True)

    def get_slow_queries(self, threshold: float = 1.0, limit: int = 10) -> List[Dict]:
        """
        获取慢操作

        Args:
            threshold: 慢操作阈值（秒）
            limit: 返回数量限制

        Returns:
            慢操作列表
        """
        result = []
        for name, stats in self.stats.items():
            if stats["count"] > 0 and stats["total_time"] / stats["count"] > threshold:
                result.append({
                    "name": name,
                    "avg_time": stats["total_time"] / stats["count"],
                    "count": stats["count"],
                })
        return sorted(result, key=lambda x: x["avg_time"], reverse=True)[:limit]

    def reset(self, name: Optional[str] = None):
        """
        重置统计数据

        Args:
            name: 操作名称，None表示重置所有
        """
        if name:
            if name in self.stats:
                del self.stats[name]
        else:
            self.stats.clear()

    def print_summary(self):
        """打印性能摘要"""
        logger.info("=" * 60)
        logger.info("性能分析摘要")
        logger.info("=" * 60)

        for stat in self.get_stats()[:10]:  # 只显示前10个
            logger.info(
                f"{stat['name']:30s} | "
                f"调用: {stat['count']:6d} | "
                f"平均: {stat['avg_time']*1000:8.2f}ms | "
                f"总计: {stat['total_time']:8.2f}s"
            )

        logger.info("=" * 60)


# 全局实例
_profiler: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """获取全局性能分析器实例"""
    global _profiler
    if _profiler is None:
        _profiler = Profiler()
    return _profiler


def profile_function(name: Optional[str] = None):
    """
    函数装饰器 - 性能分析

    Args:
        name: 分析名称，None使用函数名

    使用示例:
        @profile_function("expensive_operation")
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        profiler = get_profiler()

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            profile_name = name or f"{func.__module__}.{func.__name__}"
            with profiler.profile(profile_name):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            profile_name = name or f"{func.__module__}.{func.__name__}"
            with profiler.profile(profile_name):
                return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class AsyncProfiler:
    """异步性能分析器"""

    def __init__(self):
        self.profiler = get_profiler()

    async def profile_async(self, name: str, coro):
        """
        分析异步操作

        Args:
            name: 分析名称
            coro: 协程对象

        Returns:
            协程结果
        """
        with self.profiler.profile(name):
            return await coro

    async def batch_profile(self, operations: List[tuple[str, any]]) -> List[any]:
        """
        批量分析异步操作

        Args:
            operations: [(name, coroutine), ...] 列表

        Returns:
            结果列表
        """
        results = []
        for name, coro in operations:
            result = await self.profile_async(name, coro)
            results.append(result)
        return results


# 性能分析上下文管理器
def profile_block(name: str):
    """代码块性能分析上下文管理器"""
    return get_profiler().profile(name)
