# -*- coding: utf-8 -*-
"""
告警规则模块

提供预定义的告警规则
"""
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timedelta

from .alert_manager import AlertManager, AlertRule, AlertSeverity


class SystemConditions:
    """系统条件检查函数"""

    @staticmethod
    def create_cpu_threshold(threshold: float = 80.0) -> Callable[[], bool]:
        """CPU使用率阈值检查"""
        async def check() -> bool:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent > threshold
        return check

    @staticmethod
    def create_memory_threshold(threshold_mb: float = 1024.0) -> Callable[[], bool]:
        """内存使用阈值检查"""
        async def check() -> bool:
            import psutil
            memory_mb = psutil.virtual_memory().used / 1024 / 1024
            return memory_mb > threshold_mb
        return check

    @staticmethod
    def create_disk_threshold(threshold_percent: float = 90.0) -> Callable[[], bool]:
        """磁盘使用率阈值检查"""
        async def check() -> bool:
            import psutil
            disk_percent = psutil.disk_usage('/').percent
            return disk_percent > threshold_percent
        return check

    @staticmethod
    def create_api_error_rate(threshold: float = 0.05) -> Callable[[], bool]:
        """API错误率阈值检查"""
        async def check() -> bool:
            from ..performance.metrics import get_metrics_collector
            metrics = get_metrics_collector()

            total = metrics.get_counter("requests.total")
            errors = metrics.get_counter("responses.500")

            if total == 0:
                return False

            error_rate = errors / total
            return error_rate > threshold
        return check

    @staticmethod
    def create_api_latency_threshold(threshold_ms: float = 1000.0) -> Callable[[], bool]:
        """API延迟阈值检查"""
        async def check() -> bool:
            from ..performance.metrics import get_metrics_collector
            metrics = get_metrics_collector()

            # 获取最近50个请求的平均响应时间
            metric = metrics.get_metric("request.duration")
            if not metric or len(metric) < 10:
                return False

            recent_times = [point.value for point in list(metric)[-50:]]
            avg_time = sum(recent_times) / len(recent_times)

            return avg_time > threshold_ms / 1000  # 转换为秒
        return check

    @staticmethod
    def create_cache_hit_rate_threshold(threshold: float = 0.5) -> Callable[[], bool]:
        """缓存命中率阈值检查"""
        async def check() -> bool:
            from ..middleware.performance import get_cache_middleware
            cache_middleware = get_cache_middleware()

            stats = cache_middleware.get_stats()
            hit_rate = stats.get("hit_rate", 1.0)

            return hit_rate < threshold
        return check


class PredefinedRules:
    """预定义告警规则"""

    @staticmethod
    def high_cpu_usage() -> AlertRule:
        """高CPU使用率告警"""
        return AlertRule(
            rule_id="high_cpu_usage",
            name="高CPU使用率",
            description=f"CPU使用率超过80%",
            severity=AlertSeverity.WARNING,
            condition=SystemConditions.create_cpu_threshold(80.0),
            check_interval=60,
            cooldown=300,
        )

    @staticmethod
    def high_memory_usage() -> AlertRule:
        """高内存使用率告警"""
        return AlertRule(
            rule_id="high_memory_usage",
            name="高内存使用",
            description=f"内存使用超过1GB",
            severity=AlertSeverity.WARNING,
            condition=SystemConditions.create_memory_threshold(1024.0),
            check_interval=60,
            cooldown=300,
        )

    @staticmethod
    def high_disk_usage() -> AlertRule:
        """高磁盘使用率告警"""
        return AlertRule(
            rule_id="high_disk_usage",
            name="高磁盘使用率",
            description=f"磁盘使用率超过90%",
            severity=AlertSeverity.ERROR,
            condition=SystemConditions.create_disk_threshold(90.0),
            check_interval=300,
            cooldown=600,
        )

    @staticmethod
    def high_api_error_rate() -> AlertRule:
        """高API错误率告警"""
        return AlertRule(
            rule_id="high_api_error_rate",
            name="高API错误率",
            description="API错误率超过5%",
            severity=AlertSeverity.ERROR,
            condition=SystemConditions.create_api_error_rate(0.05),
            check_interval=30,
            cooldown=60,
        )

    @staticmethod
    def slow_api_requests() -> AlertRule:
        """慢API请求告警"""
        return AlertRule(
            rule_id="slow_api_requests",
            name="API响应缓慢",
            description="API平均响应时间超过1秒",
            severity=AlertSeverity.WARNING,
            condition=SystemConditions.create_api_latency_threshold(1000.0),
            check_interval=30,
            cooldown=120,
        )

    @staticmethod
    def low_cache_hit_rate() -> AlertRule:
        """低缓存命中率告警"""
        return AlertRule(
            rule_id="low_cache_hit_rate",
            name="缓存命中率低",
            description="缓存命中率低于50%",
            severity=AlertSeverity.WARNING,
            condition=SystemConditions.create_cache_hit_rate_threshold(0.5),
            check_interval=300,
            cooldown=600,
        )

    @staticmethod
    def database_connection_failure() -> AlertRule:
        """数据库连接失败告警"""
        async def check_db() -> bool:
            try:
                from ...db import get_postgres_client
                client = await get_postgres_client()
                return not await client.health_check()
            except:
                return True

        return AlertRule(
            rule_id="database_connection_failure",
            name="数据库连接失败",
            description="无法连接到PostgreSQL数据库",
            severity=AlertSeverity.CRITICAL,
            condition=check_db,
            check_interval=30,
            cooldown=60,
        )

    @staticmethod
    def redis_connection_failure() -> AlertRule:
        """Redis连接失败告警"""
        async def check_redis() -> bool:
            try:
                from ...cache import get_cache_manager
                cache = get_cache_manager()
                # 尝试ping
                await cache._get_client().ping()
                return False
            except:
                return True

        return AlertRule(
            rule_id="redis_connection_failure",
            name="Redis连接失败",
            description="无法连接到Redis缓存",
            severity=AlertSeverity.ERROR,
            condition=check_redis,
            check_interval=30,
            cooldown=60,
        )


async def setup_default_alerts(
    alert_manager: AlertManager,
    notifiers: Optional[Dict[str, Any]] = None
):
    """
    设置默认告警规则

    Args:
        alert_manager: 告警管理器
        notifiers: 通知器字典 {"name": notifier_instance}
    """
    # 注册预定义规则
    rules = [
        PredefinedRules.high_cpu_usage(),
        PredefinedRules.high_memory_usage(),
        PredefinedRules.high_disk_usage(),
        PredefinedRules.high_api_error_rate(),
        PredefinedRules.slow_api_requests(),
        PredefinedRules.low_cache_hit_rate(),
        PredefinedRules.database_connection_failure(),
        PredefinedRules.redis_connection_failure(),
    ]

    for rule in rules:
        alert_manager.register_rule(rule)

    # 注册通知器
    # 注册默认日志通知器
    from .notifiers import LogNotifier
    alert_manager.register_notifier("log", LogNotifier())

    # 注册额外的通知器
    if notifiers:
        for name, notifier in notifiers.items():
            alert_manager.register_notifier(name, notifier)

    from loguru import logger
    logger.info(f"已注册 {len(rules)} 个默认告警规则")
