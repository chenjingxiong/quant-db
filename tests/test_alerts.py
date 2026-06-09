# -*- coding: utf-8 -*-
"""
告警系统测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from backend.alerts import (
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    setup_default_alerts,
)
from backend.alerts.notifiers import (
    WebhookNotifier,
    SlackNotifier,
    LogNotifier,
)


# ===========================
# AlertManager Tests
# ===========================

@pytest.mark.asyncio
async def test_alert_manager_initialization():
    """测试告警管理器初始化"""
    manager = AlertManager()

    assert manager is not None
    assert len(manager.get_active_alerts()) == 0
    assert len(manager.notifiers) == 0
    assert len(manager.rules) == 0


@pytest.mark.asyncio
async def test_register_rule():
    """测试注册告警规则"""
    manager = AlertManager()

    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=60,
        cooldown=300,
    )

    manager.register_rule(rule)

    assert "test_rule" in manager.rules
    assert manager.rules["test_rule"].name == "测试规则"


@pytest.mark.asyncio
async def test_register_notifier():
    """测试注册通知器"""
    manager = AlertManager()
    notifier = LogNotifier()

    manager.register_notifier("log", notifier)

    assert "log" in manager.notifiers


@pytest.mark.asyncio
async def test_trigger_alert():
    """测试触发告警"""
    manager = AlertManager()
    notifier = Mock()
    notifier.send_safe = AsyncMock()

    manager.register_notifier("mock", notifier)

    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=60,
        cooldown=0,
    )

    manager.register_rule(rule)

    # 触发告警
    await manager._trigger_alert(rule, {"test": "data"})

    # 检查通知器被调用
    assert notifier.send_safe.called

    # 检查告警被记录
    alerts = manager.get_active_alerts()
    assert len(alerts) > 0


@pytest.mark.asyncio
async def test_alert_cooldown():
    """测试告警冷却期"""
    manager = AlertManager()

    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=1,
        cooldown=10,
    )

    manager.register_rule(rule)

    # 第一次检查应该可以触发
    can_trigger_1 = await rule.should_trigger()
    assert can_trigger_1 is True

    # 标记为已触发（记录触发时间）
    rule.mark_triggered()

    # 冷却期内不应该触发
    can_trigger_2 = await rule.should_trigger()
    assert can_trigger_2 is False


@pytest.mark.asyncio
async def test_acknowledge_alert():
    """测试确认告警"""
    manager = AlertManager()

    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=60,
        cooldown=0,
    )

    manager.register_rule(rule)
    await manager._trigger_alert(rule, {})

    # acknowledge_alert uses rule_id as key in active_alerts
    await manager.acknowledge_alert("test_rule", user="test_user")

    # 检查状态
    updated_alerts = manager.get_active_alerts()
    assert updated_alerts[0]["status"] == AlertStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_auto_resolve_alert():
    """测试自动解决告警"""
    manager = AlertManager()

    condition_met = [True]

    async def test_condition():
        return condition_met[0]

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=1,
        cooldown=0,
    )

    manager.register_rule(rule)

    # 触发告警
    await manager._check_rules()

    alerts = manager.get_active_alerts()
    assert len(alerts) > 0

    # 条件不再满足
    condition_met[0] = False

    # 自动解决检查
    await manager._check_auto_resolve()

    # 检查告警已解决
    active_alerts = manager.get_active_alerts()
    assert all(a["status"] == AlertStatus.RESOLVED for a in active_alerts)


# ===========================
# AlertRule Tests
# ===========================

def test_alert_rule_creation():
    """测试告警规则创建"""
    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=60,
        cooldown=300,
    )

    assert rule.rule_id == "test_rule"
    assert rule.name == "测试规则"
    assert rule.severity == AlertSeverity.WARNING
    assert rule.enabled is True


def test_alert_rule_enable_disable():
    """测试启用/禁用规则"""
    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=60,
        cooldown=300,
    )

    assert rule.enabled is True

    rule.enabled = False
    assert rule.enabled is False

    rule.enabled = True
    assert rule.enabled is True


# ===========================
# Notifier Tests
# ===========================

@pytest.mark.asyncio
async def test_log_notifier():
    """测试日志通知器"""
    notifier = LogNotifier()

    # 创建模拟告警
    alert = Mock()
    alert.title = "测试告警"
    alert.message = "测试消息"
    alert.severity = Mock()
    alert.severity.value = "warning"

    # 应该不抛出异常
    await notifier.send(alert)

    # 测试已解决状态
    await notifier.send(alert, resolved=True)


@pytest.mark.asyncio
async def test_webhook_notifier():
    """测试Webhook通知器"""
    notifier = WebhookNotifier(url="http://localhost:8000/webhook")

    alert = Mock()
    alert.id = "test_alert_1"
    alert.title = "测试告警"
    alert.message = "测试消息"
    alert.severity = Mock()
    alert.severity.value = "warning"
    alert.created_at = datetime.now()
    alert.metadata = {"key": "value"}

    # 使用mock来避免实际HTTP请求
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        await notifier.send(alert)

        # 验证post被调用
        assert mock_client.return_value.__aenter__.return_value.post.called


@pytest.mark.asyncio
async def test_notifier_disabled():
    """测试禁用的通知器"""
    notifier = LogNotifier()
    notifier.enabled = False

    alert = Mock()
    alert.title = "测试"
    alert.message = "消息"
    alert.severity = Mock()
    alert.severity.value = "info"

    # 不应该抛出异常
    await notifier.send_safe(alert)


# ===========================
# AlertSeverity Tests
# ===========================

def test_alert_severity_values():
    """测试告警严重级别"""
    assert AlertSeverity.INFO.value == "info"
    assert AlertSeverity.WARNING.value == "warning"
    assert AlertSeverity.ERROR.value == "error"
    assert AlertSeverity.CRITICAL.value == "critical"


# ===========================
# AlertStatus Tests
# ===========================

def test_alert_status_values():
    """测试告警状态"""
    assert AlertStatus.ACTIVE.value == "active"
    assert AlertStatus.RESOLVED.value == "resolved"
    assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
    assert AlertStatus.SILENCED.value == "silenced"


# ===========================
# Setup Functions Tests
# ===========================

@pytest.mark.asyncio
async def test_setup_default_alerts():
    """测试设置默认告警"""
    manager = AlertManager()
    notifiers = {"log": LogNotifier()}

    await setup_default_alerts(manager, notifiers)

    # 检查规则已注册
    assert len(manager.rules) > 0

    # 检查常见规则存在
    assert "high_cpu_usage" in manager.rules
    assert "high_memory_usage" in manager.rules
    assert "database_connection_failure" in manager.rules


@pytest.mark.asyncio
async def test_alert_stats():
    """测试告警统计"""
    manager = AlertManager()

    async def test_condition():
        return True

    rule = AlertRule(
        rule_id="test_rule",
        name="测试规则",
        description="测试描述",
        severity=AlertSeverity.WARNING,
        condition=test_condition,
        check_interval=60,
        cooldown=0,
    )

    manager.register_rule(rule)

    # 触发几个告警
    await manager._trigger_alert(rule, {})
    await manager._trigger_alert(rule, {})

    stats = manager.get_alert_stats()

    assert "total_alerts" in stats
    assert "active_alerts" in stats
    assert "severity_breakdown" in stats
