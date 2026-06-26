# 量化智投 —— 一站式股票量化交易平台

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> 让每个投资者都能用上专业级的量化交易工具

## 这是什么

**量化智投**是一款面向个人投资者的量化交易平台，集成**策略编写 → 回测分析 → 参数优化 → 蒙特卡洛验证 → 模拟交易 → 风控管理**全链路。

不需要写复杂的工程代码，用 Python 编写策略逻辑，一键回测看效果。

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/quanttrader.git
cd quanttrader

# 2. 安装依赖
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd ..

# 3. 启动后端 (默认 http://localhost:8000)
cd backend && uvicorn app.main:app --reload &

# 4. 启动前端 (默认 http://localhost:3000)
cd frontend && npm run dev

# 5. 打开浏览器访问 http://localhost:3000
```

> **Docker 部署**：`docker compose up -d`（需要 PostgreSQL，详见下方说明）

## 功能概览

```
┌─────────────────────────────────────────────────────────┐
│                     量化智投 工作流                        │
│                                                         │
│   📊 数据获取 ──→ 🧠 策略编写 ──→ ⚡ 回测执行              │
│       │                                    │            │
│       └── akshare/Tushare                  ├── 绩效指标    │
│                                            ├── 资金曲线    │
│   🔧 参数优化 ←────────────────────────────┤              │
│       │                                    │              │
│       └── 网格搜索                          ├── 蒙特卡洛    │
│                                            └── 压力测试    │
│   🛡️ 风控检查 ←── 💰 模拟交易 ←─────────────┘              │
│       │              │                                   │
│       ├── 日亏损熔断   ├── 订单管理                        │
│       ├── 仓位上限     ├── 持仓追踪                        │
│       └── 止损机制     └── A股费用模型                      │
└─────────────────────────────────────────────────────────┘
```

### 核心功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **数据模块** | A股日K线数据同步（akshare）、股票搜索、多数据源适配 | ✅ |
| **策略引擎** | Python 策略编写、backtrader 回测核心、3个内置策略模板 | ✅ |
| **回测分析** | 绩效指标（夏普/回撤/胜率/卡尔玛）、资金曲线、交易明细 | ✅ |
| **参数优化** | 自动网格搜索、多目标优化（夏普/收益/胜率） | ✅ |
| **蒙特卡洛** | Bootstrap 重采样、收益分布直方图、P5/P95 分析、亏损概率 | ✅ |
| **压力测试** | 暴跌/阴跌/震荡情景模拟 | ✅ |
| **模拟交易** | Paper Trading、订单状态机、持仓管理、A股佣金+印花税 | ✅ |
| **风控引擎** | 8条风控规则、日亏损熔断、仓位上限、止损、频率限制 | ✅ |
| **用户系统** | JWT 注册/登录、密码哈希、Token 认证 | ✅ |

### 内置策略模板

| 策略 | 描述 |
|------|------|
| **双均线交叉** | 短期均线上穿长期均线买入，下穿卖出 |
| **动量突破** | 价格突破N日最高点时买入，跌破N日最低点时卖出 |
| **网格交易** | 设定价格区间内按固定间距分批买入卖出 |

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.11+)
- **回测引擎**: backtrader
- **数据库**: PostgreSQL + TimescaleDB → 开发环境默认 SQLite
- **缓存**: Redis
- **数据源**: akshare（免费）/ tushare（专业）
- **认证**: JWT + SHA-256 密码哈希

### 前端
- **框架**: React 18 + TypeScript + Vite
- **UI 组件**: Ant Design 5
- **图表**: ECharts 5
- **代码编辑器**: Monaco Editor (VS Code 内核)
- **路由**: React Router 6

### 基础设施
- **部署**: Docker Compose（5个容器：app + db + redis + frontend + nginx）
- **定时任务**: APScheduler（数据同步）

## 项目结构

```
quanttrader/
├── backend/                    # Python 后端 (FastAPI)
│   ├── app/
│   │   ├── api/                # REST API 路由
│   │   │   ├── auth.py         # 认证（注册/登录）
│   │   │   ├── data.py         # 股票数据
│   │   │   ├── strategy.py     # 策略 CRUD
│   │   │   ├── backtest.py     # 回测/优化/蒙特卡洛
│   │   │   └── trade.py        # 模拟交易/风控
│   │   ├── domain/             # 领域逻辑
│   │   │   ├── strategy/       # 策略引擎 + 回测 + 优化
│   │   │   ├── backtest/       # 绩效指标 + 蒙特卡洛
│   │   │   ├── trade/          # 模拟交易撮合
│   │   │   ├── risk/           # 风控引擎
│   │   │   └── user/           # 用户认证
│   │   └── infrastructure/     # 基础设施
│   │       ├── data/           # 数据适配器 + 同步
│   │       └── persistence/    # 数据库模型
│   └── alembic/                # 数据库迁移
├── frontend/                   # React 前端
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx       # 仪表盘
│       │   ├── StrategyEditor.tsx  # 策略编写/回测/优化
│       │   ├── BacktestView.tsx    # 回测历史/蒙特卡洛
│       │   ├── TradePanel.tsx      # 模拟交易/风控
│       │   └── DataCenter.tsx      # 数据中心
│       └── api/                # API 客户端
├── docker-compose.yml         # Docker 部署
└── nginx.conf                 # Nginx 配置
```

## API 文档

启动后端后访问 `http://localhost:8000/docs` 查看完整 Swagger 文档。

### 主要端点

```
认证:    POST /api/auth/register, /login  ·  GET /me
数据:    GET  /api/data/symbols, /kline   ·  POST /sync/stocks, /sync/daily
策略:    CRUD /api/strategy/              ·  GET /templates
回测:    POST /api/backtest/run, /optimize, /compare
         GET  /api/backtest/results, /results/:id
         GET  /api/backtest/results/:id/monte-carlo, /stress-test
交易:    GET  /api/trade/account, /orders
         POST /api/trade/order, /price
风控:    GET  /api/trade/risk/status      ·  POST /risk/reset
```

## 开发路线图

### ✅ MVP（已完成）
- 策略编写 → 回测执行 → 绩效指标 → 资金曲线图表
- 3 个内置策略模板
- 股票搜索 + akshare 数据同步

### ✅ V1.0（已完成）
- 参数优化（自动网格搜索）
- 风控引擎（8条规则）
- 模拟交易（Paper Trading）
- 回测对比

### ✅ V2.0（已完成）
- JWT 用户认证
- 蒙特卡洛模拟分析
- 压力测试

### 🔜 计划中
- [ ] 实盘券商对接（vnpy 网关）
- [ ] 策略社区（分享/排行/评论）
- [ ] 分钟线/Tick 数据
- [ ] 因子归因分析
- [ ] 多策略组合优化
- [ ] 移动端适配
- [ ] WebSocket 实时行情推送

## Docker 部署

```bash
docker compose up -d
```

服务分布：
- 前端：`http://localhost` (Nginx → Vite)
- 后端 API：`http://localhost/api`
- Swagger 文档：`http://localhost:8000/docs`

## 参与贡献

欢迎提 Issue 和 PR。

## 许可

MIT License
