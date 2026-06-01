# -*- coding: utf-8 -*-
"""
性能监控中间件

提供API请求性能监控和分析
"""
import time
import asyncio
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger

from ..performance.metrics import get_metrics_collector
from ..performance.profiler import get_profiler


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(
        self,
        app: ASGIApp,
        enable_profiling: bool = True,
        slow_request_threshold: float = 1.0,
        enable_metrics: bool = True,
    ):
        """
        初始化性能监控中间件

        Args:
            app: ASGI应用
            enable_profiling: 是否启用性能分析
            slow_request_threshold: 慢请求阈值（秒）
            enable_metrics: 是否启用指标收集
        """
        super().__init__(app)
        self.enable_profiling = enable_profiling
        self.slow_request_threshold = slow_request_threshold
        self.enable_metrics = enable_metrics

        self.metrics_collector = get_metrics_collector() if enable_metrics else None
        self.profiler = get_profiler() if enable_profiling else None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并收集性能数据"""
        # 跳过健康检查端点
        if request.url.path == "/health":
            return await call_next(request)

        # 生成请求标识
        request_id = request.headers.get("X-Request-ID", f"{id(request)}")
        start_time = time.perf_counter()

        # 记录请求开始
        if self.metrics_collector:
            self.metrics_collector.inc("requests.total", tags={
                "method": request.method,
                "path": request.url.path,
            })

        # 执行请求
        try:
            response = await call_next(request)
            status = response.status_code
            error = None
        except Exception as e:
            status = 500
            error = str(e)
            raise
        finally:
            # 计算请求时间
            duration = time.perf_counter() - start_time

            # 记录性能数据
            if self.profiler:
                endpoint = f"{request.method} {request.url.path}"
                self.profiler.record(endpoint, duration, success=(error is None))

            if self.metrics_collector:
                self.metrics_collector.timing(
                    "request.duration",
                    duration,
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(status),
                    }
                )

                # 记录状态码
                self.metrics_collector.inc(
                    f"responses.{status}",
                    tags={"method": request.method, "path": request.url.path}
                )

            # 慢请求警告
            if duration > self.slow_request_threshold:
                logger.warning(
                    f"慢请求: {request.method} {request.url.path} "
                    f"耗时 {duration*1000:.2f}ms | 状态: {status}"
                )

        # 添加性能响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration*1000:.2f}ms"

        return response


class QueryPerformanceMiddleware:
    """查询性能中间件（用于数据库查询）"""

    def __init__(
        self,
        enable_query_logging: bool = True,
        slow_query_threshold: float = 0.5,
    ):
        """
        初始化查询性能中间件

        Args:
            enable_query_logging: 是否记录查询日志
            slow_query_threshold: 慢查询阈值（秒）
        """
        self.enable_query_logging = enable_query_logging
        self.slow_query_threshold = slow_query_threshold

    async def execute_query(
        self,
        query_func: Callable,
        query: str,
        *args,
        **kwargs
    ):
        """
        执行查询并记录性能

        Args:
            query_func: 查询函数
            query: SQL语句
            *args: 查询参数
            **kwargs: 额外参数

        Returns:
            查询结果
        """
        start_time = time.perf_counter()

        try:
            result = await query_func(query, *args, **kwargs)
            duration = time.perf_counter() - start_time
            success = True
        except Exception as e:
            duration = time.perf_counter() - start_time
            success = False
            logger.error(f"查询失败: {query[:100]}... 错误: {e}")
            raise

        # 记录查询性能
        if self.enable_query_logging or duration > self.slow_query_threshold:
            query_summary = query[:100].replace('\n', ' ')
            log_level = logger.warning if duration > self.slow_query_threshold else logger.debug

            log_level(
                f"查询: {query_summary} | "
                f"耗时: {duration*1000:.2f}ms | "
                f"成功: {success}"
            )

        return result

    def log_query_stats(self, stats: dict):
        """
        记录查询统计信息

        Args:
            stats: 统计信息字典
        """
        logger.info(
            f"查询统计 | "
            f"总数: {stats.get('total', 0)} | "
            f"慢查询: {stats.get('slow', 0)} | "
            f"失败: {stats.get('failed', 0)} | "
            f"平均耗时: {stats.get('avg_time', 0)*1000:.2f}ms"
        )


class CacheHitRateMiddleware:
    """缓存命中率监控"""

    def __init__(self):
        self._hits = 0
        self._misses = 0
        self._errors = 0

    def record_hit(self, cache_type: str = "default"):
        """记录缓存命中"""
        self._hits += 1

    def record_miss(self, cache_type: str = "default"):
        """记录缓存未命中"""
        self._misses += 1

    def record_error(self, cache_type: str = "default"):
        """记录缓存错误"""
        self._errors += 1

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hits + self._misses + self._errors
        if total == 0:
            return {
                "hits": 0,
                "misses": 0,
                "errors": 0,
                "hit_rate": 0.0,
            }

        return {
            "hits": self._hits,
            "misses": self._misses,
            "errors": self._errors,
            "hit_rate": self._hits / (self._hits + self._misses),
        }

    def reset(self):
        """重置统计"""
        self._hits = 0
        self._misses = 0
        self._errors = 0


# 全局实例
_cache_middleware: Optional[CacheHitRateMiddleware] = None


def get_cache_middleware() -> CacheHitRateMiddleware:
    """获取全局缓存中间件实例"""
    global _cache_middleware
    if _cache_middleware is None:
        _cache_middleware = CacheHitRateMiddleware()
    return _cache_middleware
