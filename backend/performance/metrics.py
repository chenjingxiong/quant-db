# -*- coding: utf-8 -*-
"""
指标收集器

收集和导出系统性能指标
"""
import time
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
from loguru import logger
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_points: int = 1000):
        """
        初始化指标收集器

        Args:
            max_points: 每个指标保留的最大数据点数
        """
        self.max_points = max_points
        self._metrics: Dict[str, deque] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}

    def inc(self, name: str, value: float = 1.0, tags: Optional[Dict] = None):
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增加值
            tags: 标签
        """
        key = self._make_key(name, tags)
        self._counters[key] += value

    def dec(self, name: str, value: float = 1.0, tags: Optional[Dict] = None):
        """
        减少计数器

        Args:
            name: 指标名称
            value: 减少值
            tags: 标签
        """
        key = self._make_key(name, tags)
        self._counters[key] -= value

    def set(self, name: str, value: float, tags: Optional[Dict] = None):
        """
        设置仪表值

        Args:
            name: 指标名称
            value: 值
            tags: 标签
        """
        key = self._make_key(name, tags)
        self._gauges[key] = value

    def record(self, name: str, value: float, tags: Optional[Dict] = None):
        """
        记录时序指标

        Args:
            name: 指标名称
            value: 值
            tags: 标签
        """
        key = self._make_key(name, tags)

        if key not in self._metrics:
            self._metrics[key] = deque(maxlen=self.max_points)

        self._metrics[key].append(MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        ))

    def timing(self, name: str, duration: float, tags: Optional[Dict] = None):
        """
        记录耗时指标

        Args:
            name: 指标名称
            duration: 耗时（秒）
            tags: 标签
        """
        self.record(f"{name}.duration", duration, tags)
        self.inc(f"{name}.count", 1.0, tags)

    def get_metric(self, name: str, tags: Optional[Dict] = None) -> Optional[deque]:
        """获取指标数据"""
        key = self._make_key(name, tags)
        return self._metrics.get(key)

    def get_counter(self, name: str, tags: Optional[Dict] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, tags: Optional[Dict] = None) -> Optional[float]:
        """获取仪表值"""
        key = self._make_key(name, tags)
        return self._gauges.get(key)

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "series": {
                name: [
                    {
                        "timestamp": point.timestamp,
                        "value": point.value,
                        "tags": point.tags
                    }
                    for point in points
                ]
                for name, points in self._metrics.items()
            }
        }

    def reset(self):
        """重置所有指标"""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()

    def _make_key(self, name: str, tags: Optional[Dict]) -> str:
        """生成指标键"""
        if not tags:
            return name

        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"


class SystemMetricsCollector:
    """系统指标收集器"""

    def __init__(self):
        self.process = psutil.Process()

    def collect_cpu_metrics(self) -> Dict[str, float]:
        """收集CPU指标"""
        return {
            "cpu_percent": self.process.cpu_percent(),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        }

    def collect_memory_metrics(self) -> Dict[str, float]:
        """收集内存指标"""
        mem_info = self.process.memory_info()
        return {
            "memory_rss": mem_info.rss / 1024 / 1024,  # MB
            "memory_vms": mem_info.vms / 1024 / 1024,  # MB
            "memory_percent": self.process.memory_percent(),
            "memory_available": psutil.virtual_memory().available / 1024 / 1024 / 1024,  # GB
        }

    def collect_io_metrics(self) -> Dict[str, float]:
        """收集IO指标"""
        io_counters = self.process.io_counters()
        return {
            "io_read_count": io_counters.read_count,
            "io_write_count": io_counters.write_count,
            "io_read_bytes": io_counters.read_bytes,
            "io_write_bytes": io_counters.write_bytes,
        }

    def collect_network_metrics(self) -> Dict[str, float]:
        """收集网络指标"""
        net_io = psutil.net_io_counters()
        return {
            "net_bytes_sent": net_io.bytes_sent,
            "net_bytes_recv": net_io.bytes_recv,
            "net_packets_sent": net_io.packets_sent,
            "net_packets_recv": net_io.packets_recv,
        }

    def collect_disk_metrics(self) -> Dict[str, float]:
        """收集磁盘指标"""
        disk_usage = psutil.disk_usage('/')
        return {
            "disk_total": disk_usage.total / 1024 / 1024 / 1024,  # GB
            "disk_used": disk_usage.used / 1024 / 1024 / 1024,  # GB
            "disk_free": disk_usage.free / 1024 / 1024 / 1024,  # GB
            "disk_percent": disk_usage.percent,
        }

    def collect_all(self) -> Dict[str, Dict[str, float]]:
        """收集所有系统指标"""
        return {
            "cpu": self.collect_cpu_metrics(),
            "memory": self.collect_memory_metrics(),
            "io": self.collect_io_metrics(),
            "network": self.collect_network_metrics(),
            "disk": self.collect_disk_metrics(),
        }


# 全局实例
_metrics_collector: Optional[MetricsCollector] = None
_system_metrics_collector: Optional[SystemMetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_system_metrics_collector() -> SystemMetricsCollector:
    """获取全局系统指标收集器实例"""
    global _system_metrics_collector
    if _system_metrics_collector is None:
        _system_metrics_collector = SystemMetricsCollector()
    return _system_metrics_collector
