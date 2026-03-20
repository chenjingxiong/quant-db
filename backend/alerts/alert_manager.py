# -*- coding: utf-8 -*-
"""
告警管理器

管理告警规则、触发和通知
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger
import json


class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


class Alert:
    """告警对象"""

    def __init__(
        self,
        rule_id: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        metadata: Optional[Dict] = None,
    ):
        self.id = f"{rule_id}_{datetime.now().timestamp()}"
        self.rule_id = rule_id
        self.severity = severity
        self.title = title
        self.message = message
        self.metadata = metadata or {}
        self.status = AlertStatus.ACTIVE
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.acknowledged_by: Optional[str] = None
        self.acknowledged_at: Optional[datetime] = None
        self.resolved_at: Optional[datetime] = None
        self.notification_count = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notification_count": self.notification_count,
        }


class AlertRule:
    """告警规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: AlertSeverity,
        condition: Callable[[], bool],
        check_interval: int = 60,
        enabled: bool = True,
        cooldown: int = 300,
        notifiers: Optional[List[str]] = None,
    ):
        """
        初始化告警规则

        Args:
            rule_id: 规则ID
            name: 规则名称
            description: 描述
            severity: 严重级别
            condition: 检查函数（返回True触发告警）
            check_interval: 检查间隔（秒）
            enabled: 是否启用
            cooldown: 冷却时间（秒）
            notifiers: 通知器列表
        """
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity
        self.condition = condition
        self.check_interval = check_interval
        self.enabled = enabled
        self.cooldown = cooldown
        self.notifiers = notifiers or []

        self._last_triggered: Optional[datetime] = None
        self._trigger_count = 0

    def should_trigger(self) -> bool:
        """检查是否应该触发告警"""
        if not self.enabled:
            return False

        # 冷却时间检查
        if self._last_triggered:
            elapsed = (datetime.now() - self._last_triggered).total_seconds()
            if elapsed < self.cooldown:
                return False

        return self.condition()

    def mark_triggered(self):
        """标记为已触发"""
        self._last_triggered = datetime.now()
        self._trigger_count += 1


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._notifiers: Dict[str, Any] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False

    def register_rule(self, rule: AlertRule):
        """注册告警规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"注册告警规则: {rule.name} ({rule.rule_id})")

    def unregister_rule(self, rule_id: str):
        """注销告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"注销告警规则: {rule_id}")

    def register_notifier(self, name: str, notifier: Any):
        """注册通知器"""
        self._notifiers[name] = notifier
        logger.info(f"注册通知器: {name}")

    async def start_monitoring(self, check_interval: int = 30):
        """启动监控循环"""
        if self._is_running:
            logger.warning("告警监控已在运行")
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(check_interval))
        logger.info("告警监控已启动")

    async def stop_monitoring(self):
        """停止监控循环"""
        if not self._is_running:
            return

        self._is_running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("告警监控已停止")

    async def _monitor_loop(self, interval: int):
        """监控循环"""
        while self._is_running:
            try:
                await self._check_rules()
                await self._check_auto_resolve()
            except Exception as e:
                logger.error(f"监控循环错误: {e}")

            await asyncio.sleep(interval)

    async def _check_rules(self):
        """检查所有规则"""
        for rule in self.rules.values():
            if rule.should_trigger():
                await self._trigger_alert(rule)
                rule.mark_triggered()

    async def _trigger_alert(self, rule: AlertRule):
        """触发告警"""
        # 检查是否已有活跃告警
        existing_alert = self.active_alerts.get(rule.rule_id)
        if existing_alert and existing_alert.status == AlertStatus.ACTIVE:
            # 更新现有告警
            existing_alert.updated_at = datetime.now()
            existing_alert.notification_count += 1
            return

        # 创建新告警
        alert = Alert(
            rule_id=rule.rule_id,
            severity=rule.severity,
            title=rule.name,
            message=rule.description,
            metadata={
                "trigger_count": rule._trigger_count,
                "check_interval": rule.check_interval,
            }
        )

        self.active_alerts[rule.rule_id] = alert
        self.alert_history.append(alert)

        # 发送通知
        await self._send_notifications(alert)

        logger.warning(f"告警触发: {rule.name} - {rule.description}")

    async def _check_auto_resolve(self):
        """检查自动解决"""
        for rule_id, alert in list(self.active_alerts.items()):
            if alert.status != AlertStatus.ACTIVE:
                continue

            rule = self.rules.get(rule_id)
            if not rule:
                continue

            # 检查条件是否已恢复
            if not rule.condition():
                await self._resolve_alert(rule_id)

    async def _resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()

            # 发送解决通知
            await self._send_notifications(alert, resolved=True)

            logger.info(f"告警已解决: {alert.title}")

    async def acknowledge_alert(self, alert_id: str, user: str):
        """确认告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = user
            alert.acknowledged_at = datetime.now()
            logger.info(f"告警已确认: {alert.title} by {user}")

    async def _send_notifications(self, alert: Alert, resolved: bool = False):
        """发送通知"""
        for notifier_name in alert.metadata.get("notifiers", []):
            notifier = self._notifiers.get(notifier_name)
            if notifier:
                try:
                    await notifier.send(alert, resolved=resolved)
                except Exception as e:
                    logger.error(f"发送通知失败 ({notifier_name}): {e}")

    def get_active_alerts(self) -> List[Dict]:
        """获取活跃告警"""
        return [alert.to_dict() for alert in self.active_alerts.values()]

    def get_alert_stats(self) -> Dict:
        """获取告警统计"""
        total = len(self.alert_history)
        active = len([a for a in self.active_alerts.values() if a.status == AlertStatus.ACTIVE])

        severity_counts = {}
        for alert in self.alert_history:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_alerts": total,
            "active_alerts": active,
            "severity_breakdown": severity_counts,
        }


# 全局实例
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
