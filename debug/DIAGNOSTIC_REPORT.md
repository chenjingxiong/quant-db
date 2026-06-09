# Quant_DB 项目问题诊断报告

## 诊断时间
2026-03-13

## 项目概述
Quant_DB 是一个量化金融数据采集系统，使用 FastAPI + TDengine + Redis 构建，支持股票、期货、指数等数据的采集和存储。

---

## 已发现的问题

### 严重问题（Critical）

#### 1. Python 依赖未安装
- **问题**: 核心依赖包未安装（taos, pytdx, fastapi 等）
- **影响**: 后端服务无法启动
- **解决方案**: 在 Docker 容器内安装依赖：
  ```bash
  docker-compose run backend pip install -r requirements.txt
  ```
  或者使用虚拟环境：
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

---

### 代码问题（已修复 ✓）

#### 2. 异步事件循环 API 弃用问题
- **问题**: 4 个文件使用了已弃用的 `asyncio.get_event_loop()`
- **受影响文件**:
  - `backend/storage/tdengine_client.py`
  - `backend/adapters/pytdx_adapter.py`
  - `backend/adapters/modtdx_adapter.py`
  - `backend/adapters/qmt_adapter.py`
- **修复方案**: 创建了 `backend/utils/async_helper.py` 兼容性模块，替换所有 `asyncio.get_event_loop()` 为 `get_event_loop()`
- **状态**: ✓ 已修复

---

### 已解决的问题

#### 3. 前端构建产物
- **问题**: `frontend/dist` 目录不存在
- **状态**: ✓ 已创建占位符（实际前端需要完整构建）

---

### 潜在问题（Warnings）

#### 4. 全局变量并发问题
- **问题**: `backend/api/app.py` 中的 `td_client` 全局变量可能导致并发访问问题
- **建议**: 考虑使用依赖注入或连接池管理

#### 5. TDengine 连接池竞争条件
- **问题**: `TDEngineClient._get_connection()` 方法在并发场景下可能存在竞争条件
- **建议**: 增强连接池的线程安全性

#### 6. Python 版本兼容性
- **当前版本**: Python 3.13.5
- **要求**: Python 3.9+
- **注意**: Python 3.13 是最新版本，某些库可能不完全兼容

#### 7. 前端不完整
- **问题**: `frontend/` 目录缺少 `package.json` 和构建配置
- **影响**: 无法使用 npm 构建完整的前端应用
- **建议**: 需要添加完整的 Vue/React 项目结构

---

## 修复步骤

### 自动修复（已完成）
✓ 修复了 asyncio.get_event_loop() 弃用问题  
✓ 创建了前端占位符（允许 Docker 启动）

### 手动修复（需要执行）

1. **安装 Python 依赖**（在 Docker 内或虚拟环境中）
   ```bash
   docker-compose run backend pip install -r requirements.txt
   ```

2. **完善前端**（可选，如果需要完整的前端功能）
   ```bash
   # 需要添加完整的 Vue/React 项目
   cd frontend
   npm create vite@latest . -- --template vue
   npm install
   npm run build
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

---

## 文件变更记录

### 新增文件
- `backend/utils/async_helper.py` - 异步兼容性辅助模块
- `debug/verify_issues.py` - 问题诊断脚本
- `debug/DIAGNOSTIC_REPORT.md` - 本报告
- `frontend/dist/index.html` - 前端占位符

### 修改文件
- `backend/storage/tdengine_client.py` - 修复异步 API 使用
- `backend/adapters/pytdx_adapter.py` - 修复异步 API 使用
- `backend/adapters/modtdx_adapter.py` - 修复异步 API 使用
- `backend/adapters/qmt_adapter.py` - 修复异步 API 使用

---

## 验证

可以使用以下命令验证修复效果：
```bash
python3 debug/verify_issues.py
```

---

## 总结

- **已修复**: 
  - asyncio 弃用 API 问题
  - 前端占位符（允许 Docker 启动）
  
- **待完成**: 
  - 安装 Python 依赖（在 Docker 容器内执行）
  - 完善前端项目结构（可选）
  
- **风险评估**: 中 - 代码问题已修复，依赖需要在容器内安装
