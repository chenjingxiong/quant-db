# -*- coding: utf-8 -*-
"""
Prometheus指标端点测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

import backend.performance.metrics as perf_metrics
from backend.api.routes import metrics as metrics_route


@pytest.mark.asyncio
async def test_metrics_endpoint_basic():
    """测试指标端点基本响应"""
    mock_sys_collector = Mock()
    mock_sys_collector.collect_all.return_value = {
        "cpu": {"cpu_percent": 10.5},
        "memory": {"memory_rss": 256.0, "memory_percent": 5.0},
        "disk": {"disk_percent": 45.0},
    }

    mock_app_collector = Mock()
    mock_app_collector.get_counter = Mock(side_effect=lambda x: 100.0)

    with patch.object(perf_metrics, "get_system_metrics_collector", return_value=mock_sys_collector), \
         patch.object(perf_metrics, "get_metrics_collector", return_value=mock_app_collector), \
         patch("backend.api.app.get_scheduler", return_value=None):

        response = await metrics_route.prometheus_metrics()

        assert response.status_code == 200
        body = response.body.decode()
        assert "quant_db_cpu_percent" in body
        assert "quant_db_memory_rss_mb" in body
        assert "quant_db_requests_total" in body


@pytest.mark.asyncio
async def test_metrics_endpoint_no_system():
    """测试指标端点（系统指标不可用）"""
    with patch.object(perf_metrics, "get_system_metrics_collector",
               side_effect=Exception("psutil not available")), \
         patch.object(perf_metrics, "get_metrics_collector",
               side_effect=Exception("metrics not available")), \
         patch("backend.api.app.get_scheduler", return_value=None):

        response = await metrics_route.prometheus_metrics()

        assert response.status_code == 200
        body = response.body.decode()
        assert "ERROR" in body or len(body) > 0


@pytest.mark.asyncio
async def test_metrics_endpoint_with_scheduler():
    """测试指标端点（带采集调度器）"""
    mock_scheduler = Mock()
    mock_scheduler.get_stats = Mock(return_value={
        "is_running": True,
        "total_tasks": 5,
    })

    with patch.object(perf_metrics, "get_system_metrics_collector",
               side_effect=Exception("skip")), \
         patch.object(perf_metrics, "get_metrics_collector",
               side_effect=Exception("skip")), \
         patch("backend.api.app.get_scheduler", return_value=mock_scheduler):

        response = await metrics_route.prometheus_metrics()

        body = response.body.decode()
        assert "quant_db_collector_running 1" in body
        assert "quant_db_collector_tasks 5" in body


@pytest.mark.asyncio
async def test_metrics_content_type():
    """测试指标端点Content-Type"""
    with patch.object(perf_metrics, "get_system_metrics_collector",
               side_effect=Exception("skip")), \
         patch.object(perf_metrics, "get_metrics_collector",
               side_effect=Exception("skip")), \
         patch("backend.api.app.get_scheduler", return_value=None):

        response = await metrics_route.prometheus_metrics()

        assert "text/plain" in response.media_type
