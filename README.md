# eduAI — AI 智慧教育云平台

产品需求：[PRD.md](./PRD.md) · P0 步骤：[docs/P0-STEPS.md](./docs/P0-STEPS.md)

> **部署方式**：不使用 Docker。本地三进程启动即可演示。

## 快速启动

```bash
# 一键启动 API + 学员端 + 管理端
./start.sh

# 首次或依赖缺失时
./start.sh --install

# 查看状态 / 停止 / 重启
./start.sh status
./start.sh stop
./start.sh restart
```

也可分终端手动启动：

```bash
# 终端 1：API（SQLite 自动建库 + 种子数据）
python3 -m pip install -r apps/api/requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir apps/api

# 终端 2：学员端
npm install --prefix apps/web
npm run dev --prefix apps/web

# 终端 3：管理端
npm install --prefix apps/admin
npm run dev --prefix apps/admin
```

| 服务 | 地址 |
|------|------|
| 学员端 | http://127.0.0.1:5173/ |
| 管理端 | http://127.0.0.1:5174/ |
| API / OpenAPI | http://127.0.0.1:8000/docs |

> 学员端与管理端是**两个独立前端**。在 `:5173` 登录任意账号都留在学员端；管理员 / 教师可点顶栏「系统管理后台 / 教师工作台」进入 `:5174`。后台退出后会回到 `:5173` 未登录主页。

根目录也可：`npm run dev`（学员端）· `npm run dev:admin`（管理端）· `npm run dev:api`（后端）。

### 种子账号

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 管理员 | `admin@edu.ai` | `admin123` |
| 教师 | `teacher@edu.ai` | `teacher123` |
| 学员 | `student@edu.ai` | `student123` |

数据库文件：`apps/api/data/eduai_p0.db`（首次启动自动创建并灌入演示数据）。

### 运维备份

```bash
./tools/backup.sh                 # 默认写入 backups/eduai-时间戳/
./tools/backup.sh /path/to/dir    # 指定输出目录
```

备份内容：SQLite 库文件 + `apps/api/app/static`（含词汇配图等）。

## P0 能力一览

| 模块 | 说明 |
|------|------|
| AI 互动课堂 | 幻灯 / 测验 / 模拟 / PBL 四场景 |
| 几何动图实验室 | edulab 交互课页 + 进度 |
| 英语陪练 | 情景对话 + 语音识别 / TTS |
| 青少年 AI 编程 | 浏览器内练习场 |
| 管理后台 | 仪表盘、用户/教师/课程/班级、题库试卷、公告、订单、AI 助手、知识库、PPT、审计、设置 |
| 学员中心 | 打卡、今日计划、公告、客观题练习、会员模拟下单、学习进度 |
| 账号与权限 | JWT + RBAC（admin / teacher / student）+ 审计日志 |
| **AI 学伴对话** | SSE 流式对话、知识库引用、停止生成；无 Key 时本地演示 |
| **后台 AI 配置** | Provider（OpenAI 兼容）、Prompt 版本、调用用量看板 |
| **主观题批改** | AI 初评 + 教师复核 + 抽样质检（管理端「批改复核」） |
| **错题本 / 学情 / 消息** | 错题沉淀、个人/班级薄弱点、系统通知；学情 CSV 导出 |
| **电子书 / 几何挂课** | 读物阅读；课页挂到课时 API |
| **向量知识库** | 文档切片 + 本地哈希向量检索；管理端可试检索 |
| **每日单词 / 美文** | 翻卡 + 词根词缀拆解 + 意思配图 + 学习偏好设置；美文阅读流 |
| **我爱背单词** | 独立课程：中考 800 词库、docx 真实配图、艾宾浩斯复习、每日测验打卡得星、30★兑会员；四级/六级/雅思/托福词库位预留 |
| **小学数学计算专项** | 1–6 年级计算题库、每日一页、草稿自动保存续作、计时判分、错题订正、首页待办提醒 |
| **PPT 导出 / 合规** | 管理端 PPTX 下载；学员端个人数据导出与账号注销；`tools/backup.sh` 备份 |
| **工作流编排** | 事件规则引擎：批改/反馈自动通知、积压巡检催办、执行日志；管理端可编排开关 |
| **租户用量包** | 多租户配额（Token/次数）；对话扣减；管理端开通套餐与消耗看板；个人中心可见学校配额 |
| **LTI 简易对接** | `/api/v1/lti/launch` 资源链接启动 + `/lti/demo` 模拟 LMS；跳转学员端 `/auth?token=` |
| **语音评分** | 英语陪练识别后给出 0–100 表达分 |
| **学情导出 / 教师工作台** | 平台·班级 CSV；教师 `:5174/hub` 简化入口 |
| **模板库 / 反馈** | 试卷·PPT 模板；学员反馈工单 |
| **薄弱点推荐** | `/recommend` 按错题推题并回写错题本；推送带题单深链 |
| **LLM 成本看板** | 日期筛选、可配单价、CSV 导出 |
| **几何知识点练习** | 课页↔题目显式关联；变式可复现洗牌 |
| **开放 API** | Token + 权限勾选；`/api/v1/public/v1/*` |
| **样本回流** | 来源/未导出筛选；JSON / JSONL；外部微调任务（Chat JSONL + 演示推进 / Webhook） |
| **读题 / 化学微观 / 变式练习** | `/courses/geometry-lab/vision`；化学课页；课页内可核对巩固题 |
| **学习路径** | 学员端 `/path`：错题→课页→练习→日课 |
| **工作流看板** | 管理端 `/workflows`：批改/质检/反馈阶段聚合 |
| **系统管理后台** | `apps/admin`：仪表盘运营指标、学员会员/活跃度、教师班级、AI Token/API Key |

### AI 配置（P1）

在管理端 **AI 配置** 填写 OpenAI 兼容接口，或在 `apps/api/.env`：

```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

然后点击「从环境变量导入」。学员端入口：http://127.0.0.1:5173/ai

### 知识库 Embedding（可选）

在 `apps/api/.env`：

```
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

未配置时自动使用本地哈希向量；也可复用已配置的 LLM Provider（OpenAI 兼容）。管理端「知识库」可查看向量后端并重建索引。

### LTI / 用量包

- 管理端：**学员运营 → 租户用量包**（`/billing`）
- LTI 演示启动：http://127.0.0.1:8000/api/v1/lti/demo
- 工具配置：`GET /api/v1/lti/config`（Launch URL 供 LMS 填写）

### 外部微调（演示）

管理端 **样本回流**：回流样本 →「创建微调任务」组装 Chat JSONL。可选在 `apps/api/.env`：

```
FINETUNE_WEBHOOK_URL=https://your-trainer.example/hooks/eduai
```

未配置时任务留在本地，可用「推进演示」模拟 queued→submitted→running→succeeded。


## 可选配置

### 英语神经 TTS（推荐 Edge，免 Key）

默认使用微软 Edge 神经音色（`edge-tts`），支持男女声与句间自然停顿，**不依赖 DeepSeek/OpenAI**。

```bash
pip install edge-tts   # 已写入 apps/api/requirements.txt
```

可选环境变量（`apps/api/.env`）：

```
TTS_ENGINE=auto          # auto | edge | openai
TTS_EDGE_ENABLED=1
# 若要用 OpenAI 语音（需单独 Key；DeepSeek 不支持 /audio/speech）：
# TTS_BASE_URL=https://api.openai.com/v1
# TTS_API_KEY=sk-...
# TTS_MODEL=gpt-4o-mini-tts
```

音色：女声 `en-US-JennyNeural` / 男声 `en-US-GuyNeural`（中文分别为晓晓 / 云希）。学员端可在「我爱背单词」切换男女声。

### 前端大模型陪练

`apps/web/.env`：

```
VITE_LLM_BASE_URL=...
VITE_LLM_API_KEY=...
VITE_LLM_MODEL=...
```

### 几何课页刷新

```bash
npm run geometry:demos
```

上游：[wy51ai/edulab](https://github.com/wy51ai/edulab)（Apache-2.0）→ `vendor/edulab`。
