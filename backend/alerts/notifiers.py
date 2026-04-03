# -*- coding: utf-8 -*-
"""
通知器模块

提供多种通知发送方式
"""
import asyncio
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from loguru import logger
import httpx


class BaseNotifier(ABC):
    """通知器基类"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    @abstractmethod
    async def send(self, alert: Any, resolved: bool = False):
        """发送通知"""
        pass

    async def send_safe(self, alert: Any, resolved: bool = False):
        """安全发送通知（捕获异常）"""
        if not self.enabled:
            return

        try:
            await self.send(alert, resolved)
        except Exception as e:
            logger.error(f"发送通知失败 ({self.name}): {e}")


class WebhookNotifier(BaseNotifier):
    """Webhook通知器"""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict] = None,
        timeout: float = 10.0,
        **kwargs
    ):
        super().__init__("webhook", **kwargs)
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout

    async def send(self, alert: Any, resolved: bool = False):
        """发送Webhook通知"""
        async with httpx.AsyncClient() as client:
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "status": "resolved" if resolved else "triggered",
                "timestamp": alert.created_at.isoformat(),
                "metadata": alert.metadata,
            }

            response = await client.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            logger.info(f"Webhook通知已发送: {self.url}")


class SlackNotifier(BaseNotifier):
    """Slack通知器"""

    def __init__(
        self,
        webhook_url: str,
        channel: str = "#alerts",
        username: str = "Quant DB Alerts",
        icon_emoji: str = ":warning:",
        **kwargs
    ):
        super().__init__("slack", **kwargs)
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji

    async def send(self, alert: Any, resolved: bool = False):
        """发送Slack通知"""
        color = {
            "info": "good",
            "warning": "warning",
            "error": "danger",
            "critical": "danger",
        }.get(alert.severity.value, "warning")

        status_emoji = "✅" if resolved else "⚠️"
        status_text = "已解决" if resolved else "触发"

        payload = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "title": f"{status_emoji} {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "严重级别", "value": alert.severity.value, "short": True},
                        {"title": "状态", "value": status_text, "short": True},
                        {"title": "时间", "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"), "short": True},
                    ],
                    "footer": f"Alert ID: {alert.id}",
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Slack通知已发送: {self.channel}")


class EmailNotifier(BaseNotifier):
    """邮件通知器"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list,
        **kwargs
    ):
        super().__init__("email", **kwargs)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    async def send(self, alert: Any, resolved: bool = False):
        """发送邮件通知"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"

        status_text = "已解决" if resolved else "触发"
        body = f"""
告警通知
--------
状态: {status_text}
级别: {alert.severity.value}
标题: {alert.title}
描述: {alert.message}

告警ID: {alert.id}
时间: {alert.created_at.strftime("%Y-%m-%d %H:%M:%S")}
详情: {json.dumps(alert.metadata, indent=2, ensure_ascii=False)}
        """

        msg.attach(MIMEText(body, "plain"))

        # 这里应该使用异步SMTP库，暂时使用同步方式
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_sync, msg)

    def _send_sync(self, msg):
        """同步发送邮件"""
        import smtplib

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)

        logger.info(f"邮件通知已发送: {msg['Subject']}")


class LogNotifier(BaseNotifier):
    """日志通知器（用于测试）"""

    def __init__(self, name: str = "log", enabled: bool = True):
        super().__init__(name, enabled)

    async def send(self, alert: Any, resolved: bool = False):
        """记录告警到日志"""
        level = logger.warning if alert.severity.value == "warning" else logger.error
        level(
            f"告警: {alert.title} | {alert.message} | "
            f"严重级别: {alert.severity.value} | 状态: {'resolved' if resolved else 'triggered'}"
        )


# 通知器工厂
_notifiers: Dict[str, type] = {
    "webhook": WebhookNotifier,
    "slack": SlackNotifier,
    "email": EmailNotifier,
    "log": LogNotifier,
}


def get_notifier(notifier_type: str, **config) -> BaseNotifier:
    """
    获取通知器实例

    Args:
        notifier_type: 通知器类型
        **config: 通知器配置

    Returns:
        通知器实例
    """
    notifier_class = _notifiers.get(notifier_type)
    if not notifier_class:
        raise ValueError(f"未知的通知器类型: {notifier_type}")

    return notifier_class(**config)
