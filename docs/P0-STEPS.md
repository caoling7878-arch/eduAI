# P0 分步交付清单（无 Docker）

> 权威范围见 `PRD.md` §10。本文跟踪执行状态。

## 决策

- **取消** Docker / Docker Compose 一键部署
- 本地进程：API `8000` + 学员端 `5173` + 管理端 `5174`
- 数据：SQLite + 本地 uploads 目录

## 步骤

| 步骤 | 内容 | 状态 |
|------|------|------|
| S0 | 热门课、账号进度、AI 课堂、主页 | ✅ |
| S1 | 域模型 + RBAC + 审计 + 种子 + 核心 CRUD API | ✅ |
| S2 | 管理端：仪表盘 / 用户 / 教师 / 课程 / 班级 | ✅ |
| S3 | 管理端：题库 / 试卷 / 公告 / 订单 / 设置 | ✅ |
| S4 | 管理端：AI 助手 / 知识库 / PPT / 几何入口 | ✅ |
| S5 | 学员端：打卡 / 计划 / 公告 / 个人中心 / 练习 | ✅ |
| S6 | 联调验收与文档 | ✅ |

## 本地启动

```bash
# 终端 1
python3 -m pip install -r apps/api/requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir apps/api

# 终端 2
npm run dev --prefix apps/web

# 终端 3
npm run dev --prefix apps/admin
```

默认管理员（种子）：`admin@edu.ai` / `admin123`
