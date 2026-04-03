# -*- coding: utf-8 -*-
"""
Prometheus指标端点

提供/metrics端点供Prometheus抓取
"""
from fastapi import APIRouter, Response
from loguru import logger

router = APIRouter()


@router.get("")
async def prometheus_metrics():
    """Prometheus指标端点"""
    metrics_text = []

    # 系统指标
    try:
        from ...performance.metrics import get_system_metrics_collector
        sys_collector = get_system_metrics_collector()
        sys = sys_collector.collect_all()

        metrics_text.append("# HELP quant_db_cpu_percent Process CPU usage percent")
        metrics_text.append("# TYPE quant_db_cpu_percent gauge")
        metrics_text.append(f'quant_db_cpu_percent {sys["cpu"]["cpu_percent"]}')

        metrics_text.append("# HELP quant_db_memory_rss_mb Process RSS memory in MB")
        metrics_text.append("# TYPE quant_db_memory_rss_mb gauge")
        metrics_text.append(f'quant_db_memory_rss_mb {sys["memory"]["memory_rss"]:.2f}')

        metrics_text.append("# HELP quant_db_memory_percent Process memory usage percent")
        metrics_text.append("# TYPE quant_db_memory_percent gauge")
        metrics_text.append(f'quant_db_memory_percent {sys["memory"]["memory_percent"]:.2f}')

        metrics_text.append("# HELP quant_db_disk_percent Disk usage percent")
        metrics_text.append("# TYPE quant_db_disk_percent gauge")
        metrics_text.append(f'quant_db_disk_percent {sys["disk"]["disk_percent"]}')
    except Exception as e:
        logger.warning(f"Failed to collect system metrics: {e}")
        metrics_text.append(f'# ERROR: system metrics unavailable: {e}')

    # 应用指标
    try:
        from ...performance.metrics import get_metrics_collector
        mc = get_metrics_collector()

        requests_total = mc.get_counter("requests.total")
        responses_500 = mc.get_counter("responses.500")
        responses_400 = mc.get_counter("responses.400")

        metrics_text.append("# HELP quant_db_requests_total Total HTTP requests")
        metrics_text.append("# TYPE quant_db_requests_total counter")
        metrics_text.append(f"quant_db_requests_total {requests_total}")

        metrics_text.append("# HELP quant_db_responses_5xx_total Total 5xx responses")
        metrics_text.append("# TYPE quant_db_responses_5xx_total counter")
        metrics_text.append(f"quant_db_responses_5xx_total {responses_500}")

        metrics_text.append("# HELP quant_db_responses_4xx_total Total 4xx responses")
        metrics_text.append("# TYPE quant_db_responses_4xx_total counter")
        metrics_text.append(f"quant_db_responses_4xx_total {responses_400}")
    except Exception as e:
        logger.warning(f"Failed to collect app metrics: {e}")

    # 采集器指标
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            stats = scheduler.get_stats()
            metrics_text.append("# HELP quant_db_collector_running Collector scheduler running")
            metrics_text.append("# TYPE quant_db_collector_running gauge")
            metrics_text.append(
                f'quant_db_collector_running {1 if stats.get("is_running") else 0}'
            )

            metrics_text.append("# HELP quant_db_collector_tasks Total collection tasks")
            metrics_text.append("# TYPE quant_db_collector_tasks gauge")
            metrics_text.append(f'quant_db_collector_tasks {stats.get("total_tasks", 0)}')
    except Exception as e:
        logger.warning(f"Failed to collect scheduler metrics: {e}")

    content = "\n".join(metrics_text) + "\n"
    return Response(content=content, media_type="text/plain; version=0.0.4")
