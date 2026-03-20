# 量化金融数据采集系统

基于 Docker 的量化金融数据采集与存储系统，支持 pytdx、modtdx、QMT 等多数据源，使用 TDengine 时序数据库存储，提供 RESTful API 和 WebSocket 实时推送。

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐
│  pytdx 数据源    │     │  modtdx 数据源  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌─────────────────────┐
         │   数据采集调度器      │
         └──────────┬──────────┘
                     ▼
         ┌─────────────────────┐
         │   数据缓存队列       │
         └──────────┬──────────┘
                     ▼
         ┌─────────────────────┐
         │   数据清洗/验证      │
         └──────────┬──────────┘
                     ▼
         ┌─────────────────────┐
         │   TDengine 数据库    │
         └──────────┬──────────┘
                     ▼
         ┌─────────────────────┐
         │   FastAPI + WebSocket│
         └─────────────────────┘
```

## 功能特性

### 数据采集
- **多数据源支持**: pytdx、modtdx、QMT
- **多数据类型**: 股票、期货、指数、板块
- **定时采集**: 支持Cron表达式配置
- **失败重试**: 自动重试机制
- **优先级队列**: 支持数据优先级处理

### 数据处理
- **数据清洗**: 去重、缺失值填充、异常值处理
- **数据验证**: 完整性、准确性、一致性检查
- **增量处理**: 基于时间戳的增量数据获取

### 数据存储
- **时序数据库**: 使用 TDengine 高效存储
- **超级表设计**: 按数据类型分类存储
- **批量写入**: 优化写入性能

### API 接口
- **RESTful API**: 完整的数据查询接口
- **WebSocket**: 实时数据推送
- **自动文档**: Swagger/OpenAPI

## 快速开始

### 1. 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 8GB+ 内存
- 20GB+ 磁盘空间

### 2. 克隆项目

```bash
cd /root/projects/Quant_DB
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据源等参数
```

### 4. 启动服务

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

### 5. 访问服务

- API 文档: http://192.168.6.8:8000/docs
- Web 界面: http://192.168.6.8:8080
- 健康检查: http://192.168.6.8:8000/health

## 项目结构

```
Quant_DB/
├── backend/                  # Python 后端
│   ├── adapters/            # 数据源适配器
│   ├── collectors/          # 数据采集
│   ├── processors/          # 数据处理
│   ├── storage/             # 数据存储
│   ├── models/              # 数据模型
│   ├── api/                 # API 接口
│   ├── config/              # 配置
│   └── utils/               # 工具
├── frontend/                # Vue3 前端
│   └── src/
│       ├── views/           # 页面
│       ├── components/      # 组件
│       ├── router/          # 路由
│       ├── store/           # 状态管理
│       └── api/             # API 封装
├── mobile/                  # React Native 移动端
│   └── src/
│       ├── screens/         # 页面
│       ├── components/      # 组件
│       └── navigation/      # 导航
├── docker/                  # Docker 配置
│   ├── nginx/               # Nginx 配置
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── logs/                    # 日志目录
├── data/                    # 数据目录
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## API 端点

### 股票数据
- `GET /api/v1/stocks/quotes?symbols=000001,600000` - 获取股票行情
- `GET /api/v1/stocks/bars?symbol=000001&interval=1day` - 获取K线数据
- `GET /api/v1/stocks/list` - 获取股票列表

### 期货数据
- `GET /api/v1/futures/quotes?symbols=IF2503` - 获取期货行情
- `GET /api/v1/futures/bars?symbol=IF2503&interval=1day` - 获取K线数据
- `GET /api/v1/futures/list` - 获取合约列表

### 指数数据
- `GET /api/v1/indices/quotes?symbols=000001` - 获取指数行情
- `GET /api/v1/indices/bars?symbol=000001&interval=1day` - 获取K线数据

### 板块数据
- `GET /api/v1/sectors/list` - 获取板块列表
- `GET /api/v1/sectors/{name}/quotes` - 获取板块行情

### 采集管理
- `GET /api/v1/collect/status` - 获取采集状态
- `POST /api/v1/collect/start` - 启动采集任务
- `POST /api/v1/collect/stop/{task_id}` - 停止采集任务

### WebSocket
```
ws://192.168.6.8:8000/ws
```

订阅消息格式:
```json
{
  "action": "subscribe",
  "topic": "stock:quotes:000001"
}
```

## 配置说明

### 数据源配置

```env
# pytdx 配置
PYTDX_HOSTS=119.147.212.81,60.12.136.250
PYTDX_PORT=7709

# QMT 配置
QMT_PATH=/data/qmt
QMT_HOST=127.0.0.1
QMT_PORT=18080
```

### 采集配置

```env
# 采集间隔（秒）
COLLECT_INTERVAL=5
# 批量大小
BATCH_SIZE=1000
# 最大重试次数
MAX_RETRY=3
```

## 数据源说明

### pytdx (通达信)
- 免费、稳定
- 支持股票、期货、指数
- 无需认证

### modtdx (修改版通达信)
- 性能更好
- 需要从源码安装

### QMT (迅投)
- 支持实盘交易
- 需要迅投客户端

## 部署说明

### 生产环境部署

1. 修改 `.env` 文件中的配置
2. 确保 TDengine 数据持久化
3. 配置 SSL 证书（HTTPS）
4. 调整资源限制

### 监控和维护

- 日志文件: `./logs/`
- 数据备份: TDengine 数据目录
- 健康检查: `/health` 端点

## 开发指南

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python -m backend.main
```

### 添加新数据源

1. 在 `backend/adapters/` 创建新的适配器类
2. 继承 `BaseAdapter` 实现所需方法
3. 在采集器中注册新适配器

## 许可证

MIT License
