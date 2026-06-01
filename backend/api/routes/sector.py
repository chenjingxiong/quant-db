# -*- coding: utf-8 -*-
"""
板块数据API路由
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
import re
from loguru import logger

router = APIRouter()


def _validate_identifier(name: str) -> str:
    """Validate SQL identifier to prevent injection."""
    if not re.match(r'^[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*$', name):
        raise HTTPException(status_code=400, detail=f"Invalid identifier: {name}")
    return name


@router.get("/list")
async def get_sector_list(
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
):
    """
    获取板块列表

    返回行业板块或概念板块列表
    """
    try:
        # 这里返回常见板块
        # 实际应用中可以从数据库或数据源获取
        if sector_type == "industry":
            sectors = [
                {"name": "银行", "code": "BK0001"},
                {"name": "证券", "code": "BK0002"},
                {"name": "保险", "code": "BK0003"},
                {"name": "房地产", "code": "BK0004"},
                {"name": "医药", "code": "BK0005"},
                {"name": "电子", "code": "BK0006"},
                {"name": "计算机", "code": "BK0007"},
                {"name": "通信", "code": "BK0008"},
            ]
        elif sector_type == "concept":
            sectors = [
                {"name": "人工智能", "code": "GN0001"},
                {"name": "新能源汽车", "code": "GN0002"},
                {"name": "芯片", "code": "GN0003"},
                {"name": "5G", "code": "GN0004"},
                {"name": "碳中和", "code": "GN0005"},
            ]
        else:
            sectors = []

        return {
            "sectors": sectors,
            "total": len(sectors),
        }

    except Exception as e:
        logger.error(f"Get sector list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sector_name}/quotes")
async def get_sector_quotes(
    sector_name: str,
):
    """获取板块行情"""
    try:
        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            # 返回模拟数据
            return {
                "name": sector_name,
                "index_value": 1000.0,
                "change_percent": 1.5,
                "up_count": 30,
                "down_count": 20,
                "stocks": [],
            }

        # 从数据库查询
        table_name = f"sector_quotes_{_validate_identifier(sector_name.replace(' ', '_'))}"
        sql = f"SELECT * FROM {table_name} ORDER BY ts DESC LIMIT 1"
        data = await client.query(sql)

        if data:
            return data[0]
        else:
            # 无数据时返回模拟数据
            return {
                "name": sector_name,
                "index_value": 1000.0,
                "change_percent": 1.5,
                "up_count": 30,
                "down_count": 20,
                "stocks": [],
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get sector quotes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sector_name}/stocks")
async def get_sector_stocks(
    sector_name: str,
):
    """获取板块成分股"""
    try:
        # 这里返回模拟数据
        # 实际应用中可以从数据库查询
        return {
            "sector_name": sector_name,
            "stocks": [
                {"symbol": "600000", "name": "浦发银行", "weight": 5.2},
                {"symbol": "601398", "name": "工商银行", "weight": 4.8},
            ],
            "total": 2,
        }

    except Exception as e:
        logger.error(f"Get sector stocks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
