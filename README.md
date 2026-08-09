# eduAI — AI 智慧教育云平台

**AI 原生 · 教学生产闭环 · 易部署可落地**

面向学校、教培机构与企业内训的一站式智慧教学云，用「内容生产 × 学习行为 × 评估反馈」闭环，让教与学更高效、更可衡量。

产品需求：[PRD.md](./PRD.md) · P0 步骤：[docs/P0-STEPS.md](./docs/P0-STEPS.md) · 许可证：[MIT](./LICENSE)

> **部署方式**：不使用 Docker。本地三进程（API + 学员端 + 管理端）即可演示与交付；亦可打包成 Windows / macOS 桌面安装包一键安装。

---

## 桌面安装包（Windows / macOS）

面向最终用户的本地客户端：安装后出现 **eduAI** 应用图标，双击即可启动本地服务并打开系统界面（无需手动起三个进程）。

| 平台 | 安装包 | 安装方式 |
|------|--------|----------|
| Windows | `install.exe` | 双击安装，自动创建桌面与开始菜单快捷方式 |
| macOS | `eduAI-*.dmg` | 打开 DMG，将 **eduAI** 拖入「应用程序」 |

**使用**

1. 安装完成后点击 **eduAI** 图标启动  
2. 学员端：窗口内首页；管理端：菜单「帮助 → 管理端」或访问 `/admin/`  
3. 演示账号：`admin@edu.ai` / `admin123` · `teacher@edu.ai` / `teacher123` · `student@edu.ai` / `student123`

**开发者如何打安装包**

```bash
# 在对应操作系统上执行（服务端二进制不可跨平台交叉编译）
./tools/desktop/build.sh mac    # 在 Mac 上生成 DMG → desktop/dist/

# Windows（推荐 PowerShell，含管理端 /admin 与 Embedding 修复校验）
powershell -ExecutionPolicy Bypass -File tools\desktop\build.ps1
# 产物：desktop\dist\install.exe
```

也可在 GitHub Actions 手动触发工作流 **Desktop Installers**（`.github/workflows/desktop-release.yml`），下载 `eduai-windows-installer` 产物中的 `install.exe`。  
Windows / macOS 安装包均包含：管理端 SPA 路由回退、Embedding 配置与向量维度对齐。

> 说明：桌面版将学员端与管理端构建为静态资源，由内嵌 API 单进程托管（默认端口 `18765`），数据保存在系统用户目录下的 eduAI 应用数据文件夹。

---

## 产品概述与价值主张

eduAI 把人工智能真正嵌进教学业务，而不是“挂一个聊天窗口”的伪 AI。平台同时提供：

- **学员学习门户**：课堂、练习、背词、几何动图、英语陪练、AI 编程与学伴对话
- **机构管理后台**：课程班级、题库试卷、智能批改、知识库、学情报表、订单会员与工作流编排
- **开放能力**：OpenAI 兼容大模型接入、LTI 简易对接、开放 API

**一句话定位**：用 AI 把「备课 — 授课 — 练习 — 批改 — 学情 — 辅导」串成可运营的闭环，帮助学校与机构降本增效、提升学习效果与续费率。

### 三大差异化

| 差异点 | 说明 |
|--------|------|
| **AI 能力业务化** | 助手、知识库、出题、课件、批改、薄弱点推荐全部内嵌业务流，可配置、可审计 |
| **数据可管可控** | 题库、课件、学情、错题可沉淀、可导出；JWT + RBAC + 操作审计，满足校园 / 政企合规 |
| **部署与集成友好** | 本地三进程即可演示；大模型可替换供应商；可对接 LMS（LTI）与开放 API |

---

## 我们解决什么问题

| 行业痛点 | eduAI 解法 |
|----------|------------|
| 教学资源分散，课件 / 题库难复用 | 统一课程、题库、试卷、模板与知识库资源中心 |
| 主观题批改标准不一、教师负担重 | AI 初评 + 教师复核 + 抽样质检工作流 |
| 学情看不见、薄弱点难跟进 | 错题本、班级 / 个人学情、薄弱点推题与学习路径 |
| 英语 / 数学等专项缺乏日常闭环 | 背单词打卡、小学计算每日一页、英语语音陪练 |
| 几何抽象难讲清 | 可交互 2D / 3D 几何动图课页，「算对」与「看懂」同源 |
| 机构缺运营抓手 | 仪表盘、会员订单、租户用量包、公告与反馈工单 |

---

## 双端产品体验

### 学员端：学习门户，一眼看懂今天学什么

学员登录后进入学习门户。首页集中呈现每日任务、打卡、今日计划与课程进度；侧栏按「学习中心 / 学习资源 / 我的学习」分区。打开即学、学完即测、错题即复盘——无需培训即可上手。

地址：http://127.0.0.1:5173/

### 管理端：运营与教学一站掌控

面向校长、运营与教师：仪表盘 KPI、学员 / 教师 / 班级 / 课程、题库试卷、批改复核、知识库与 AI 配置、学情报表、订单会员等。教师也可通过简化「教师工作台」(`:5174/hub`) 快速进入常用教学功能。

地址：http://127.0.0.1:5174/

> 学员端与管理端是**两个独立前端**。在 `:5173` 登录任意账号都留在学员端；管理员 / 教师可点顶栏进入管理端。后台退出后回到 `:5173` 未登录主页。

---

## 核心功能亮点

### AI 学伴：会引用知识库的专属助教

多角色助手（如几何助教、口语陪练），SSE 流式对话，可绑定机构知识库。后台可配置模型 Provider、Prompt 版本与助手人设——用自己的教材与话术服务学员，而不是通用公网闲聊。无 API Key 时亦可本地演示。

### 几何动图实验室：拖一拖就懂

基于可交互课页（上游 [edulab](https://github.com/wy51ai/edulab)），覆盖立体几何与圆锥曲线等难点。课页可挂入课时，支持对话讲解与图片读题，练习与知识点显式关联，形成「看懂 — 练习 — 巩固」闭环。适合公开课演示与家长沟通。

### 我爱背单词：科学记忆 + 语音 + 打卡激励

中考高频 800 词库（预留四六级 / 雅思 / 托福位），艾宾浩斯复习、词根词缀拆解、真实配图与神经 TTS 朗读。每日新学与复习目标清晰，测验打卡得星，可用星星兑换会员——把坚持变成可见的成长。

### 英语陪练与小学数学计算专项

- **英语陪练**：情景对话、语音识别与 0–100 表达评分，降低「开口难」
- **小学计算专项**：1–6 年级题库，每日一页、草稿续作、计时判分、错题订正，首页待办提醒

### AI 互动课堂与个性化学习路径

课堂支持幻灯 / 测验 / 模拟 / PBL 等多场景；学习路径（`/path`）将错题 → 课页 → 练习 → 日课串成下一步行动，减少「学完不知练什么」的空窗。另有青少年 AI 编程浏览器练习场、电子书阅读、化学微观课页等。

### 内容测评与智能批改中心

题库与试卷支撑日常测验；主观题走 **AI 初评 → 教师复核 → 抽样质检**。工作流规则可自动催办积压、触达通知，减轻教师事务性负担。

### 知识库、PPT 助手与学情报表

支持上传 **PDF / Markdown / TXT / DOCX** 教材（也可粘贴文本），自动切片向量化；可从知识库一键 **生成 AI 课程**（章节课时 + 可选绑定助教）与 **题库题目**；学伴对话引用教材片段。PPT 助手辅助大纲到课件；学情支持班级 / 个人薄弱点与 CSV 导出。

### 个人中心与合规

学员可查看学习进度、会员状态与学校配额；支持个人数据导出与账号注销。机构侧有审计日志与备份工具（`./tools/backup.sh`）。

---

## 为什么易用、为什么实用

**易用**

- 信息架构克制：学习门户侧栏分区清晰，常用功能三步内可达
- 任务驱动首页：待办、打卡、进度条把「今天做什么」说清楚
- 降低认知负担：学伴快捷提问、背单词一键听读、几何一键开课页
- 双端分工：学员端与管理端分离，角色权限分明

**实用**

| 角色 | 价值 |
|------|------|
| 教师 | 几何动图 + PPT + 知识库，备课更快、讲解更直观 |
| 学员 | 日课打卡、错题路径、AI 辅导，形成习惯与反馈闭环 |
| 机构 | 仪表盘、订单会员、用量包、审计日志，运营可度量 |
| 集成商 | 开放 API / LTI，可嵌入现有教务或 LMS |

---

## 适用客户与交付方式

| 客户类型 | 典型切入场景 |
|----------|--------------|
| K12 学校 / 区域教研 | 几何可视化公开课、校本知识库学伴、学情周报 |
| 教培机构 | 会员体系 + 背单词 / 计算日课 + AI 批改减负 |
| 高校 / 职教实训 | AI 编程练习场、开放 API 对接实训平台 |
| 企业内训 | 知识库问答助手、测验试卷与培训学情 |
| 教育信息化集成商 | LTI / 开放 API 嵌入现有 LMS，联合交付 |

商业化路径可灵活组合：SaaS 订阅 + 会员、私有化授权、内容与定制、AI 用量包（Token / 次数配额）。大模型采用 OpenAI 兼容协议，可替换供应商，避免厂商锁定。

建议演示路径（约 30–60 分钟）：首页日课 → 几何动图 → AI 学伴 → 管理端仪表盘与批改；试点可看打卡率、错题闭环率与教师批改时长。

---

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

---

## 能力一览（技术明细）

| 模块 | 说明 |
|------|------|
| AI 互动课堂 | 幻灯 / 测验 / 模拟 / PBL 四场景 |
| 几何动图实验室 | edulab 交互课页 + 进度；课页↔题目关联；读题 / 变式练习 |
| 英语陪练 | 情景对话 + 语音识别 / TTS + 表达评分 |
| 青少年 AI 编程 | 浏览器内练习场 |
| 管理后台 | 仪表盘、用户/教师/课程/班级、题库试卷、公告、订单、AI 助手、知识库、PPT、审计、设置 |
| 学员中心 | 打卡、今日计划、公告、客观题练习、会员模拟下单、学习进度 |
| 账号与权限 | JWT + RBAC（admin / teacher / student）+ 审计日志 |
| AI 学伴对话 | SSE 流式、知识库引用、停止生成；无 Key 时本地演示 |
| 后台 AI 配置 | Provider（OpenAI 兼容）、Prompt 版本、调用用量 / LLM 成本看板 |
| 主观题批改 | AI 初评 + 教师复核 + 抽样质检 |
| 错题本 / 学情 / 消息 | 错题沉淀、个人/班级薄弱点、系统通知；学情 CSV 导出 |
| 电子书 / 几何挂课 | 读物阅读；课页挂到课时 API |
| 向量知识库 | PDF/MD/TXT/DOCX 上传解析 + 文本入库；切片向量检索；从 KB 生成课程/题库/助教 |
| 每日单词 / 美文 | 翻卡 + 词根词缀 + 配图 + 学习偏好；美文阅读流 |
| 我爱背单词 | 中考 800 词、docx 配图、艾宾浩斯、打卡得星兑会员 |
| 小学数学计算专项 | 1–6 年级、每日一页、草稿续作、计时判分、错题订正 |
| PPT 导出 / 合规 | 管理端 PPTX；个人数据导出与账号注销；`tools/backup.sh` |
| 工作流编排 | 批改/反馈自动通知、积压催办、执行日志与看板 |
| 租户用量包 | Token/次数配额；对话扣减；个人中心可见学校配额 |
| LTI 简易对接 | `/api/v1/lti/launch` + `/lti/demo`；跳转学员端 `/auth?token=` |
| 模板库 / 反馈 | 试卷·PPT 模板；学员反馈工单 |
| 薄弱点推荐 | `/recommend` 按错题推题并回写错题本 |
| 开放 API | Token + 权限勾选；`/api/v1/public/v1/*` |
| 样本回流 | JSON / JSONL 导出；外部微调任务（演示推进 / Webhook） |
| 学习路径 | 学员端 `/path`：错题→课页→练习→日课 |

---

## 可选配置

### AI 配置

在管理端 **AI 配置** 填写 OpenAI 兼容接口，或在 `apps/api/.env`：

```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

然后点击「从环境变量导入」。学员端入口：http://127.0.0.1:5173/ai

### 知识库 Embedding（可选）

管理端 **知识库 → Embedding 配置** 可选择：

| 模式 | 说明 |
|------|------|
| `hash` | 本地哈希向量（默认推荐，离线稳定，无维度错配） |
| `auto` | 已配置且连通 `/embeddings` 时用 API，否则回退哈希 |
| `api` | 强制使用 Embedding API |

或在 `apps/api/.env`：

```
EMBEDDING_MODE=auto
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

须使用支持 `/v1/embeddings` 的服务；纯对话接口（如部分 DeepSeek 部署）请用本地哈希。变更后端后请点「重建向量索引」。

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

---

让每一次学习都被看见，让每一份教学都更轻松。

—— eduAI 智慧教育云
