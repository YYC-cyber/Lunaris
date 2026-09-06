# 📚 Lunaris 项目文档

**项目版本：v1.0.0**

完整的产品设计、技术需求和实现文档。按需求查找相应的文档。

---

## 📖 核心文档（6 份）

### 1. **[01_PRD.md](01_PRD.md)** - 产品需求文档 ⭐
**阅读时间**: 15-20 分钟  
**内容**: 产品定义、目标、功能列表、商业模式、用户价值

**适合**:
- 产品经理 - 业务目标和策略
- 项目经理 - 项目范围和优先级
- 全体团队 - 产品理解

**核心内容**:
- 7 大核心功能（AI 聊天、语音、群聊、知识库等）
- 目标用户画像
- 商业模式（免费 + 付费订阅）

---

### 2. **[02_DESIGN_SYSTEM.md](02_DESIGN_SYSTEM.md)** - 设计系统 🎨
**阅读时间**: 10-15 分钟  
**内容**: 色系、排版、组件、交互原则

**适合**:
- UI/UX 设计师 - 设计规范
- 前端工程师 - 实现规范

**核心内容**:
- 紫粉色主色系 (#D4A5D4)
- 四时段背景（早中晚深夜）
- 毛玻璃设计风格

---

### 3. **[03_PROTOTYPE.md](03_PROTOTYPE.md)** - UI 原型 📱
**阅读时间**: 15-20 分钟  
**内容**: 页面流程、交互设计、用户旅程

**适合**:
- 设计师 - UI 细节
- 前端工程师 - 实现参考
- 产品经理 - 用户流程

---

### 4. **[04_SRS.md](04_SRS.md)** - 系统需求规范 🔧
**阅读时间**: 30-45 分钟  
**内容**: 技术需求（FR/NFR）、数据库设计、API 定义

**适合**:
- 后端工程师 - 技术实现
- 全栈工程师 - 系统架构
- 数据库管理员

**核心内容**:
- 20+ 个功能需求 (FR-AUTH, FR-CHAT, FR-GROUP 等)
- 数据库 SQL 定义（10+ 表）
- API 端点规范
- 非功能需求（性能、安全、可靠性）

---

### 5. **[05_TEST_REPORT.md](05_TEST_REPORT.md)** - 测试报告 ✅
**阅读时间**: 20-30 分钟  
**内容**: 功能测试结果、验证清单、已知问题

**适合**:
- QA 工程师 - 测试方法
- 开发人员 - 验证步骤
- 所有技术人员 - 系统现状

**核心内容**:
- 群聊功能测试用例
- Bug 修复验证表
- 上线前检查清单

---

### 6. **[06_IMPLEMENTATION.md](06_IMPLEMENTATION.md)** - 实现指南 🚀
**阅读时间**: 20-30 分钟  
**内容**: 部署流程、故障排查、维护指南

**适合**:
- DevOps 工程师 - 部署
- Tech Lead - 架构评审
- 开发团队 - 启动和维护

**核心内容**:
- 部署检查清单（数据库 + 后端 + 前端）
- 功能验证步骤
- 常见问题排查
- 下一步计划（Phase 3-5）

---

## 🎯 按场景快速导航

### 场景 1: 我是新手，想快速了解项目

**推荐阅读顺序** (30 分钟):
1. [01_PRD.md](01_PRD.md) - 了解产品
2. [03_PROTOTYPE.md](03_PROTOTYPE.md) - 看 UI 流程
3. [06_IMPLEMENTATION.md](06_IMPLEMENTATION.md) - 启动项目

---

### 场景 2: 我是后端工程师，要开发新功能

**推荐阅读顺序**:
1. [04_SRS.md](04_SRS.md) - 技术需求（最重要！）
2. [05_TEST_REPORT.md](05_TEST_REPORT.md) - 验证标准
3. [06_IMPLEMENTATION.md](06_IMPLEMENTATION.md) - 部署方式

---

### 场景 3: 我是前端工程师，要实现 UI

**推荐阅读顺序**:
1. [02_DESIGN_SYSTEM.md](02_DESIGN_SYSTEM.md) - 设计规范
2. [03_PROTOTYPE.md](03_PROTOTYPE.md) - 页面设计
3. [04_SRS.md](04_SRS.md) - API 接口（Ctrl+F 搜"API"）

---

### 场景 4: 我要部署项目到生产

**推荐阅读顺序**:
1. [06_IMPLEMENTATION.md](06_IMPLEMENTATION.md) - 部署清单
2. [04_SRS.md](04_SRS.md) - 性能要求
3. [05_TEST_REPORT.md](05_TEST_REPORT.md) - 验证步骤

---

### 场景 5: 我遇到 Bug 或问题

**推荐阅读**:
1. [06_IMPLEMENTATION.md](06_IMPLEMENTATION.md) - 故障排查部分
2. [05_TEST_REPORT.md](05_TEST_REPORT.md) - 已知问题列表

---

## 📊 文档快速查询

| 主题 | 在哪里找 | 关键词搜索 |
|------|---------|----------|
| 群聊功能 | SRS (04) / TEST (05) | FR-GROUP, group_chats |
| 数据库表 | SRS (04) | CREATE TABLE |
| API 端点 | SRS (04) | POST /api, GET /api |
| 设计规范 | DESIGN_SYSTEM (02) | 色系、排版、组件 |
| UI 流程 | PROTOTYPE (03) | 用户流程、交互 |
| 部署步骤 | IMPLEMENTATION (06) | 部署检查清单 |
| 已知问题 | TEST_REPORT (05) | 已知问题、待优化 |

---

## ✨ 主要功能速览

| 功能 | PRD | SRS | TEST | 状态 |
|------|-----|-----|------|------|
| AI 虚拟伴侣 | ✅ | ✅ | ✅ | 完成 |
| 多人群聊 | ✅ | ✅ | ✅ | 完成 |
| 语音交互 | ✅ | ✅ | ✅ | 完成 |
| 知识库 | ✅ | ✅ | ✅ | 完成 |
| 朋友圈 | ✅ | ✅ | ✅ | 完成 |
| @ 功能 | ✅ | ✅ | ⏳ | 进行中 |

---

## 🚀 立即开始

### 部署步骤（详见 06_IMPLEMENTATION.md）

```bash
# 1. 数据库迁移
alembic upgrade head
python scripts/init_stickers.py

# 2. 启动后端
cd /Users/yyc/PycharmProjects/Lunaris/backend
uvicorn main:app --reload

# 3. 启动前端
cd /Users/yyc/PycharmProjects/Lunaris/frontend
npm install && npm run dev

# 4. 打开浏览器
访问 http://localhost:5173
```

---

## 📈 项目状态

| 项 | 状态 | 备注 |
|----|------|------|
| 后端代码 | ✅ 完成 | 生产级别 |
| 前端代码 | ✅ 完成 | 生产级别 |
| 数据库设计 | ✅ 完成 | 11 个表 |
| 群聊功能 | ✅ 完成 | 9 规则 AI 策略 |
| 测试验证 | ✅ 完成 | 90%+ 通过 |
| **生产就绪** | ✅ **是** | 需初始化数据 |

---

## 🔗 快速链接

**技术栈**:
- 后端：FastAPI + SQLAlchemy + PostgreSQL
- 前端：Vue 3 + Pinia + Element Plus
- 通信：WebSocket + REST API

**仓库**:
- 后端：`/Users/yyc/PycharmProjects/Lunaris/backend`
- 前端：`/Users/yyc/PycharmProjects/Lunaris/frontend`
- 文档：`/Users/yyc/PycharmProjects/Lunaris/.docs`

---

## 💡 阅读建议

- **第一次读**: 按 PRD → PROTOTYPE → SRS 的顺序，建立完整理解
- **查询参考**: 用文档中的搜索功能或本表格快速查找
- **深入学习**: 集中阅读 SRS（最详细的技术文档）

---

**最后更新**: 2026-08-20  
**版本**: v1.0  
**维护者**: Tech Lead + Product Team

🎉 **选择相关文档开始阅读吧！**
