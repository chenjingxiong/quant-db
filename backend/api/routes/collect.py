# -*- coding: utf-8 -*-
"""
采集管理API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter()


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    name: str
    status: str
    enabled: bool
    total_runs: int
    success_count: int
    failed_count: int
    total_collected: int


class CollectionConfig(BaseModel):
    """采集配置"""
    data_type: str = Field(..., description="数据类型: stock/futures/index")
    data_source: str = Field(..., description="数据源: pytdx/modtdx/qmt")
    symbols: List[str] = Field(..., description="采集标的列表")
    interval: str = Field("1min", description="K线周期")
    cron: Optional[str] = Field(None, description="Cron表达式")


@router.get("/status", response_model=List[TaskStatusResponse])
async def get_collection_status():
    """获取所有采集任务状态"""
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()

        if not scheduler:
            return []

        tasks = scheduler.get_all_tasks()
        return [TaskStatusResponse(**t) for t in tasks]

    except Exception as e:
        logger.error(f"Get collection status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取单个任务状态"""
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()

        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        status = scheduler.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return TaskStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_collection(config: CollectionConfig):
    """
    启动采集任务

    根据配置创建并启动新的采集任务
    """
    try:
        from ...api.app import get_scheduler
        from ...collectors import CollectionTask
        from ...adapters import PytdxAdapter, ModtdxAdapter, QmtAdapter

        scheduler = get_scheduler()

        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        from ...config import get_settings
        settings = get_settings()

        # 选择适配器
        if config.data_source == "pytdx":
            pytdx_hosts = [h.strip() for h in settings.pytdx_hosts.split(",") if h.strip()]
            adapter = PytdxAdapter({
                "hosts": pytdx_hosts,
                "port": settings.pytdx_port,
                "timeout": settings.collect_timeout,
            })
        elif config.data_source == "modtdx":
            adapter = ModtdxAdapter()
        elif config.data_source == "qmt":
            adapter = QmtAdapter()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown data source: {config.data_source}")

        # 连接适配器
        if not await adapter.connect():
            raise HTTPException(status_code=503, detail=f"Failed to connect to {config.data_source}")

        # 创建任务
        task_id = f"{config.data_type}_{config.data_source}_{len(scheduler.get_all_tasks())}"
        task = CollectionTask(
            task_id=task_id,
            name=f"{config.data_type} collection from {config.data_source}",
            adapter=adapter,
            data_type=config.data_type,
            symbols=config.symbols,
            interval=config.interval,
            cron=config.cron,
            enabled=True,
        )

        # 注册任务
        if scheduler.register_task(task):
            return {
                "status": "success",
                "task_id": task_id,
                "message": f"Collection task started: {task_id}"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to register task")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{task_id}")
async def stop_collection(task_id: str):
    """停止采集任务"""
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()

        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        # 暂停任务
        if await scheduler.pause_task(task_id):
            return {
                "status": "success",
                "message": f"Task {task_id} stopped"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stop collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/{task_id}")
async def resume_collection(task_id: str):
    """恢复采集任务"""
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()

        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        # 恢复任务
        if await scheduler.resume_task(task_id):
            return {
                "status": "success",
                "message": f"Task {task_id} resumed"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_collection_config():
    """获取采集配置"""
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()

        if not scheduler:
            return {"tasks": []}

        tasks = scheduler.get_all_tasks()
        return {
            "tasks": tasks,
            "total": len(tasks),
        }

    except Exception as e:
        logger.error(f"Get collection config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_collection_logs(
    limit: int = 100,
    level: Optional[str] = None,
):
    """获取采集日志"""
    try:
        # 这里可以从日志文件或数据库获取采集日志
        # 暂时返回空列表
        return {
            "logs": [],
            "total": 0,
        }

    except Exception as e:
        logger.error(f"Get collection logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_collection_stats():
    """获取采集统计信息"""
    try:
        from ...api.app import get_scheduler, get_td_client
        scheduler = get_scheduler()
        client = get_td_client()

        stats = {
            "scheduler": scheduler.get_stats() if scheduler else {},
            "database": client.get_stats() if client else {},
        }

        return stats

    except Exception as e:
        logger.error(f"Get collection stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
