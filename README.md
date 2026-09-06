# Lunaris

**当前版本：v1.0.0**

融合 **AI 虚拟伴侣、智能问答社区、个人知识库** 的桌面应用。
Electron + Vue 3 客户端，Python FastAPI 后端，PostgreSQL + pgvector 数据存储。

## 📚 项目文档导航

### 🎯 核心文档（必读）
- **[产品与设计文档](.docs/README.md)** - PRD / 设计系统 / 原型 / SRS / 测试报告 / 实现指南 汇总入口

### 🗺️ 路线图和规划
- **[后续安排](.docs/后续安排.md)** - 容器化、CI/CD、监控、文档等详细计划

### 📖 产品与设计文档（`.docs/`）
- `.docs/01_PRD.md` - 产品需求文档
- `.docs/02_DESIGN_SYSTEM.md` - 设计系统规范
- `.docs/03_PROTOTYPE.md` - UI 原型与交互流程
- `.docs/04_SRS.md` - 系统需求规范（最详细的技术文档）
- `.docs/05_TEST_REPORT.md` - 测试报告
- `.docs/06_IMPLEMENTATION.md` - 实现与部署指南

## 目录结构（概览）

```
Lunaris/
├── frontend/   # Vue 3 前端（组件/页面/状态/工具）
├── backend/    # Python FastAPI 后端（模型/服务/接口/核心引擎/实时层）
├── electron/   # Electron 桌面壳（主进程/托盘/通知/快捷键）
├── scripts/    # 部署与初始化脚本
├── .docs/      # 项目文档
└── pyproject.toml  # 后端 Python 依赖（uv 管理）
```

## 快速启动

### 0. 前置条件

- **Python 3.11+** 和 **Node.js 18+**
- **uv** 包管理器：`pip install uv` 或 `brew install uv`（macOS）
- **PostgreSQL 15+** 数据库（已启动）

### 1. 后端启动

```bash
# 项目根目录
cd backend

# 安装依赖（使用 uv）
uv sync

# 配置数据库（复制环境变量模板，修改数据库连接地址）
cp .env.example .env  # 编辑 DATABASE_URL

# 初始化数据库（alembic 迁移）
uv run alembic upgrade head

# 启动后端服务（开发模式，热重载）
python -m uvicorn main:app --reload

# 或直接运行
python main.py
```

**后端访问地址：** `http://localhost:8000`
- API 文档：`http://localhost:8000/api/docs` (Swagger UI)
- 健康检查：`http://localhost:8000/health`

### 2. 前端启动（主客户端 - Vue 3）

```bash
# 项目根目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

**前端访问地址：** `http://localhost:5173`（自动打开浏览器）

### 3. 管理后台启动（React）

```bash
# 项目根目录（使用便捷启动脚本）
./start-admin.sh

# 或手动启动
cd admin-react
npm install
npm run dev
```

**管理后台访问地址：** `http://localhost:5174`
- 登录账号 / 密码：`admin` / `admin123`，`luna` / `luna123`

### 4. Electron 桌面应用

```bash
cd electron

npm install

# 开发模式
npm run dev

# 打包构建
npm run build
```

---

## 开发说明

- 每个文件头部注释 = 该文件的实现要求，按注释填充
- 后端依赖详见 `pyproject.toml`
- 实现与部署说明见 `.docs/06_IMPLEMENTATION.md`
