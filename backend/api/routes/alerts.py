# -*- coding: utf-8 -*-
"""
告警API路由

提供告警管理端点
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from pydantic import BaseModel, Field

from ...alerts import get_alert_manager, AlertStatus
from ...middleware import require_auth, require_admin

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertListResponse(BaseModel):
    """告警列表响应"""
    total: int
    active: int
    alerts: List[dict]


class AlertActionRequest(BaseModel):
    """告警操作请求"""
    action: str = Field(..., description="操作: acknowledge/resolve/silence")


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(None, description="过滤状态"),
    severity: Optional[str] = Query(None, description="过滤严重级别"),
    current_user: dict = Depends(require_auth),
):
    """
    获取告警列表

    需要认证
    """
    alert_manager = get_alert_manager()
    active_alerts = alert_manager.get_active_alerts()

    # 应用过滤
    filtered_alerts = active_alerts
    if status:
        filtered_alerts = [a for a in filtered_alerts if a["status"] == status]
    if severity:
        filtered_alerts = [a for a in filtered_alerts if a["severity"] == severity]

    return AlertListResponse(
        total=len(filtered_alerts),
        active=len([a for a in filtered_alerts if a["status"] == "active"]),
        alerts=filtered_alerts,
    )


@router.get("/stats")
async def get_alert_stats(
    current_user: dict = Depends(require_auth),
):
    """
    获取告警统计

    需要认证
    """
    alert_manager = get_alert_manager()
    stats = alert_manager.get_alert_stats()

    # 添加规则统计
    stats["total_rules"] = len(alert_manager.rules)
    stats["enabled_rules"] = len([r for r in alert_manager.rules.values() if r.enabled])

    return stats


@router.post("/{alert_id}/action")
async def alert_action(
    alert_id: str,
    request: AlertActionRequest,
    current_user: dict = Depends(require_auth),
):
    """
    对告警执行操作

    需要认证

    操作:
    - acknowledge: 确认告警
    - resolve: 解决告警
    - silence: 静音告警
    """
    alert_manager = get_alert_manager()

    if request.action == "acknowledge":
        await alert_manager.acknowledge_alert(
            alert_id,
            user=current_user.get("username", "unknown")
        )
        return {"message": "告警已确认"}

    elif request.action == "resolve":
        await alert_manager._resolve_alert(alert_id)
        return {"message": "告警已解决"}

    elif request.action == "silence":
        # 静音告警（禁用规则）
        rule = alert_manager.rules.get(alert_id)
        if rule:
            rule.enabled = False
            return {"message": "告警规则已禁用"}
        raise HTTPException(status_code=404, detail="告警规则不存在")

    else:
        raise HTTPException(status_code=400, detail=f"未知操作: {request.action}")


@router.post("/rules/{rule_id}/enable")
async def enable_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    启用告警规则

    需要管理员权限
    """
    alert_manager = get_alert_manager()
    rule = alert_manager.rules.get(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="告警规则不存在")

    rule.enabled = True
    return {"message": f"告警规则 {rule_id} 已启用"}


@router.post("/rules/{rule_id}/disable")
async def disable_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    禁用告警规则

    需要管理员权限
    """
    alert_manager = get_alert_manager()
    rule = alert_manager.rules.get(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="告警规则不存在")

    rule.enabled = False
    return {"message": f"告警规则 {rule_id} 已禁用"}


@router.get("/rules")
async def list_rules(
    current_user: dict = Depends(require_auth),
):
    """
    获取告警规则列表

    需要认证
    """
    alert_manager = get_alert_manager()

    rules = []
    for rule in alert_manager.rules.values():
        rules.append({
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "check_interval": rule.check_interval,
            "cooldown": rule.cooldown,
            "trigger_count": rule._trigger_count,
            "last_triggered": rule._last_triggered.isoformat() if rule._last_triggered else None,
        })

    return {"rules": sorted(rules, key=lambda x: x["rule_id"])}
