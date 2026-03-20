# 第6轮迭代：Docker部署优化

## 迭代概览

本迭代专注于Docker容器化部署优化，修复后端容器启动问题，优化Dockerfile和docker-compose配置，并提供便捷的部署脚本。

---

## 完成内容

### 1. docker-compose.yml 优化

**修改内容：**
- 添加 `TDENGINE_AVAILABLE=false` 环境变量，使TDengine成为可选依赖
- 将TDengine依赖从 `service_healthy` 改为 `service_started`，避免阻塞启动
- 移除 `.:/app` 卷挂载，避免权限冲突
- 将健康检查改为使用Python而非curl（更可靠）
- 添加 `start_period: 30s` 到健康检查
- 添加 `backend_config` 命名卷用于配置持久化

**关键变更：**
```yaml
environment:
  - TDENGINE_AVAILABLE=false  # TDengine设为可选

depends_on:
  tdengine:
    condition: service_started  # 不等待健康检查

healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; ..."]
  start_period: 30s  # 启动宽限期
```

### 2. Dockerfile.backend 优化

**新增功能：**
- 添加Python环境变量优化
- 使用 `--no-install-recommends` 减小镜像大小
- 创建非root用户 `appuser` 提升安全性
- 清理apt缓存减小镜像大小
- 修正启动命令使用 `backend/main.py`

**关键变更：**
```dockerfile
# 环境变量优化
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 非root用户
RUN useradd -m -u 1000 appuser
USER appuser

# 正确的启动命令
CMD ["python", "backend/main.py"]
```

### 3. 部署脚本

**Linux/macOS: scripts/deploy.sh**
- `build` - 构建所有镜像
- `rebuild` - 重新构建并启动
- `up` - 启动所有服务
- `down` - 停止所有服务
- `restart` - 重启所有服务
- `logs [service]` - 查看日志
- `status` - 查看服务状态和健康检查
- `clean` - 清理容器和卷
- `init` - 初始化数据库和配置

**Windows: scripts/deploy.bat**
- 提供与Linux脚本相同的功能

### 4. PostgreSQL初始化脚本更新

**修改：**
- 注释掉使用bcrypt的默认admin用户插入
- 添加注释说明应通过API创建用户
- 避免与新的PBKDF2密码哈希格式冲突

---

## 部署说明

### 首次部署

```bash
# 1. 初始化配置
cp .env.example .env
vim .env  # 编辑配置

# 2. 初始化数据库
./scripts/deploy.sh init

# 3. 启动所有服务
./scripts/deploy.sh up
```

### 重新部署

```bash
# 完全重新构建
./scripts/deploy.sh rebuild

# 查看服务状态
./scripts/deploy.sh status

# 查看日志
./scripts/deploy.sh logs backend
```

### Windows用户

```cmd
REM 使用批处理脚本
scripts\deploy.bat rebuild
scripts\deploy.bat status
```

---

## 服务依赖关系

```
┌─────────────┐
│  tdengine   │ (optional)
└─────────────┘
       │
┌──────▼──────┐
│  postgres   │ ─────┐
└─────────────┘      │
┌─────────────┐      ├──►  backend
│   redis     │ ─────┤
└─────────────┘      │
┌─────────────┐      │
│  rabbitmq   │ ─────┘
└─────────────┘
```

**依赖说明：**
- backend 依赖 postgres、redis、rabbitmq 健康检查
- backend 依赖 tdengine 仅启动（不等待健康）
- frontend 依赖 backend
- nginx 依赖 frontend、backend

---

## 健康检查端点

| 服务 | 健康检查命令 | 说明 |
|------|-------------|------|
| tdengine | `taos -s "SHOW DATABASES;"` | TDengine数据库 |
| redis | `redis-cli ping` | Redis缓存 |
| postgres | `pg_isready -U quant_user` | PostgreSQL数据库 |
| rabbitmq | `rabbitmq-diagnostics -q ping` | 消息队列 |
| backend | `curl http://localhost:8000/health` | 后端API |

---

## 故障排查

### 后端容器无法启动

1. 检查日志：
   ```bash
   docker logs quant_backend --tail 100
   ```

2. 常见问题：
   - TDengine连接失败：设置 `TDENGINE_AVAILABLE=false`
   - 端口冲突：检查8000端口是否被占用
   - 权限问题：确保日志目录可写

### 数据库连接失败

1. 检查容器状态：
   ```bash
   docker compose ps
   ```

2. 检查PostgreSQL日志：
   ```bash
   docker logs quant_postgres
   ```

3. 测试连接：
   ```bash
   docker exec -it quant_postgres psql -U quant_user -d quant_db
   ```

### 重新初始化数据库

```bash
# 停止并删除卷
docker compose down -v

# 重新启动
docker compose up -d
```

---

## 下一步计划

1. **CI/CD集成**
   - GitHub Actions工作流
   - 自动化测试和部署

2. **监控和日志**
   - 集成Prometheus监控
   - 日志聚合（ELK/Loki）

3. **备份策略**
   - 数据库自动备份
   - 配置文件版本控制

4. **生产优化**
   - 多阶段构建优化
   - 镜像仓库配置
   - 密钥管理（Secrets）

---

*文档生成时间: 2026-03-19*
*迭代轮次: 6*
