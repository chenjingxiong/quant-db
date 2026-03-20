# 第9轮迭代：监控告警系统

## 迭代概览

本迭代专注于监控告警系统的建立，包括告警规则管理、多通道通知、增强的健康检查和告警管理API。

---

## 完成内容

### 1. 告警模块 (`backend/alerts/`)

#### AlertManager (`alert_manager.py`)

**功能：**
- 告警规则管理
- 告警触发和冷却
- 自动解决检测
- 通知发送
- 告警历史记录

**核心类：**
- `Alert` - 告警对象
- `AlertRule` - 告警规则
- `AlertSeverity` - 严重级别 (INFO/WARNING/ERROR/CRITICAL)
- `AlertStatus` - 状态 (ACTIVE/RESOLVED/ACKNOWLEDGED/SILENCED)

#### Notifiers (`notifiers.py`)

**支持的通知通道：**
- `WebhookNotifier` - Webhook通知
- `SlackNotifier` - Slack通知
- `EmailNotifier` - 邮件通知
- `LogNotifier` - 日志通知（测试用）

#### AlertRules (`alert_rules.py`)

**预定义条件检查：**
- CPU使用率阈值
- 内存使用阈值
- 磁盘使用率阈值
- API错误率阈值
- API响应时间阈值
- 缓存命中率阈值

**预定义告警规则：**
- 高CPU使用率
- 高内存使用
- 高磁盘使用率
- 高API错误率
- API响应缓慢
- 低缓存命中率
- 数据库连接失败
- Redis连接失败

### 2. 告警API (`backend/api/routes/alerts.py`)

**端点：**
- `GET /alerts` - 获取告警列表
- `GET /alerts/stats` - 获取告警统计
- `POST /alerts/{alert_id}/action` - 执行告警操作
- `POST /alerts/rules/{rule_id}/enable` - 启用规则
- `POST /alerts/rules/{rule_id}/disable` - 禁用规则
- `GET /alerts/rules` - 获取规则列表

### 3. 增强健康检查 (`backend/api/routes/health.py`)

**新增端点：**
- `GET /health` - 基础健康检查
- `GET /health/detailed` - 详细健康检查
- `GET /health/ping` - Ping端点

**检查组件：**
- PostgreSQL健康状态
- Redis健康状态
- RabbitMQ健康状态
- TDengine健康状态（可选）
- 数据采集器状态

**响应信息：**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-20T00:00:00",
  "uptime_seconds": 1234567,
  "version": "1.0.0",
  "components": {
    "postgresql": {"name": "postgresql", "status": "healthy", ...},
    "redis": {"name": "redis", "status": "healthy", ...},
    ...
  }
}
```

---

## 告警规则配置

### 预定义告警规则

| 规则ID | 名称 | 阈值 | 严重级别 |
|--------|------|------|----------|
| high_cpu_usage | 高CPU使用率 | 80% | WARNING |
| high_memory_usage | 高内存使用 | 1GB | WARNING |
| high_disk_usage | 高磁盘使用 | 90% | ERROR |
| high_api_error_rate | 高API错误率 | 5% | ERROR |
| slow_api_requests | API响应缓慢 | 1秒 | WARNING |
| low_cache_hit_rate | 缓存命中率低 | 50% | WARNING |
| database_connection_failure | 数据库连接失败 | N/A | CRITICAL |
| redis_connection_failure | Redis连接失败 | N/A | ERROR |

### 自定义告警规则

```python
from backend.alerts import AlertRule, AlertSeverity, AlertCondition

# 创建自定义规则
custom_rule = AlertRule(
    rule_id="custom_metric",
    name="自定义指标告警",
    description="自定义指标超过阈值",
    severity=AlertSeverity.WARNING,
    condition=check_custom_condition,
    check_interval=60,
    cooldown=300,
)

# 注册到管理器
from backend.alerts import get_alert_manager
alert_manager = get_alert_manager()
alert_manager.register_rule(custom_rule)
```

---

## 告警流程

```
┌─────────────────────┐
│   监控循环 (30s)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   检查所有规则        │
│   - 系统资源          │
│   - API指标          │
│   - 缓存命中率        │
│   - 数据库连接        │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ 条件满足?   │
    └──────┬───────┘
           │
     ┌─────┴─────┐
     │ 触发告警   │
     └─────┬─────┘
           │
           ▼
┌─────────────────────┐
│   发送通知           │
│ - Slack              │
│ - Email              │
│ - Webhook            │
│ - 日志               │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│   记录告警历史       │
│   更新统计信息       │
└─────────────────────┘
```

---

## 监控仪表板

### Grafana仪表板配置

已创建的配置文件：
- `docker/grafana/provisioning/datasources/prometheus.yml`
- `docker/grafana/provisioning/dashboards/quant-db.yml`

### 关键监控指标

**系统指标：**
- CPU使用率
- 内存使用量
- 磁盘使用率
- 网络流量

**应用指标：**
- 请求数 (QPS)
- 响应时间 (P50/P95/P99)
- 错误率
- 缓存命中率

**业务指标：**
- 数据采集状态
- WebSocket连接数
- 活跃用户数

---

## 使用指南

### 启用告警系统

```python
from backend.alerts import setup_default_alerts, get_alert_manager
from backend.alerts.notifiers import WebhookNotifier, LogNotifier

# 获取告警管理器
alert_manager = get_alert_manager()

# 配置通知器
notifiers = {
    "log": LogNotifier(),
    "webhook": WebhookNotifier(
        url="https://hooks.slack.com/...",
    ),
}

# 设置默认告警
await setup_default_alerts(alert_manager, notifiers)

# 启动监控
await alert_manager.start_monitoring()
```

### 集成到应用

```python
# 在 FastAPI 应用中
from backend.api.routes import health, alerts

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])

# 在应用启动时初始化告警
@app.on_event("startup")
async def startup():
    from backend.alerts import setup_default_alerts, get_alert_manager
    from backend.alerts.notifiers import LogNotifier

    alert_manager = get_alert_manager()
    await setup_default_alerts(alert_manager, {"log": LogNotifier()})
    await alert_manager.start_monitoring()
```

---

## 项目文件更新

```
backend/
├── alerts/
│   ├── __init__.py           # 告警模块入口 [NEW]
│   ├── alert_manager.py       # 告警管理器 [NEW]
│   ├── alert_rules.py         # 告警规则 [NEW]
│   └── notifiers.py           # 通知器 [NEW]
└── api/routes/
    ├── health.py              # 增强的健康检查 [UPDATED]
    └── alerts.py              # 告警管理API [NEW]
```

---

## 下一步优化

1. **告警聚合**
   - 相似告警合并
   - 告警静默规则
   - 告警升级机制

2. **可视化监控**
   - 实时监控大屏
   - 告警历史图表
   - 性能趋势分析

3. **智能告警**
   - 基于机器学习的异常检测
   - 动态阈值调整
   - 预测性告警

---

*文档生成时间: 2026-03-20*
*迭代轮次: 9*
