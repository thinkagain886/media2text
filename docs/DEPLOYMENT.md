# media2text · 完整使用手册

> 版本：v2.0 | 最后更新：2025年4月
> 
> 本手册覆盖：项目功能介绍、架构说明、环境安装（手把手）、三种启动方式、页面功能详解、配置项说明、常见问题排查。

---

## 目录

1. [项目介绍](#1-项目介绍)
2. [功能全览](#2-功能全览)
3. [技术架构](#3-技术架构)
4. [目录结构](#4-目录结构)
5. [环境准备（从零安装）](#5-环境准备从零安装)
6. [配置文件详解](#6-配置文件详解)
7. [启动方式一：纯本地开发模式](#7-启动方式一纯本地开发模式)
8. [启动方式二：Docker 全栈模式](#8-启动方式二docker-全栈模式)
9. [启动方式三：混合模式（推荐日常开发）](#9-启动方式三混合模式推荐日常开发)
10. [页面功能详解](#10-页面功能详解)
11. [输出数据格式说明](#11-输出数据格式说明)
12. [Notion / 飞书集成指南](#12-notion--飞书集成指南)
13. [OSS 配置指南](#13-oss-配置指南)
14. [历史记录与二次处理](#14-历史记录与二次处理)
15. [常见问题与排查](#15-常见问题与排查)
16. [性能参考与建议](#16-性能参考与建议)

---

## 1. 项目介绍

**media2text** 是一个运行在本地或云端的媒体文件转文本平台。

你可以把它理解为一个**私有的、可灵活配置的"音视频内容提取器"**：

- 把会议录音、播客、课程视频、访谈音频等批量丢进来
- 系统自动把视频抽成音频，把音频转成文字
- 可选让大模型帮你总结成摘要
- 结果可以保存本地、存数据库、上传 OSS、同步到 Notion 或飞书
- 所有配置都在页面里点击完成，**不需要改代码**

### 适合谁用

| 人群 | 使用场景 |
|------|---------|
| 内容创作者 | 批量处理播客/访谈，提取文字稿 |
| 知识工作者 | 会议录音转文字+AI总结，同步飞书 |
| 研究人员 | 课程视频批量转录，存入 Notion 知识库 |
| 开发者 | 本地部署，数据不出内网，自定义扩展 |

---

## 2. 功能全览

### 2.1 核心处理流程

```
上传文件（视频/音频混合）
    ↓
自动识别文件类型
    ↓
视频 → FFmpeg 提取音频（mp3, 16kHz）
    ↓ 
音频 → 转写（本地 FunASR 或 阿里云百炼 API）
    ↓
文字 → Markdown 格式化
    ↓
可选：AI 大模型总结（通义千问）
    ↓
可选存储：本地文件 / OSS / SQLite / Supabase
    ↓
可选推送：Notion 多维表格 / 飞书多维表格
```

### 2.2 功能开关一览（主页可配置项）

| 功能 | 默认 | 说明 |
|------|------|------|
| 保存音频到本地 | ✅ 开 | 提取的音频保存到本地目录 |
| 上传音频到 OSS | ❌ 关 | 上传至阿里云 OSS，获得公网 URL |
| 开启转写 | ❌ 关 | 音频 → 文字 |
| 保存文本到本地 | ❌ 关 | 转写结果保存为 `.md` 文件 |
| 上传文本到 OSS | ❌ 关 | 转写结果上传 OSS |
| 批量模式：分开/合并 | 分开 | 合并时多文件拼成一份文稿 |
| AI 大模型总结 | ❌ 关 | 调用大模型生成摘要 |
| 推送到 Notion | ❌ 关 | 同步一条记录到 Notion 数据库 |
| 推送到飞书 | ❌ 关 | 同步一条记录到飞书多维表格 |
| 保存到历史记录 | ❌ 关 | 存入本地 SQLite 或 Supabase |

### 2.3 转写引擎对比

| 引擎 | 费用 | 前置条件 | 中文效果 | 适用场景 |
|------|------|---------|---------|---------|
| **本地 FunASR** | 免费 | 首次自动下载模型（约 500MB） | ⭐⭐⭐⭐⭐ | 中文为主，追求免费离线 |
| **阿里云百炼 API** | 按用量付费 | 需 OSS + DashScope Key | ⭐⭐⭐⭐⭐ | 不想本地跑模型，追求速度 |

> ⚠️ **重要**：使用百炼 API 时，必须同时开启「上传音频到 OSS」，因为百炼只接受公网 URL，不支持直接上传本地文件。

---

## 3. 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器                                │
│         Vue3 + Vite + Ant Design Vue 4 + Pinia              │
│         （三栏布局：文件区 | 配置区 | 结果区）               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST + SSE 实时进度
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI 后端                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  FFmpeg  │  │  FunASR  │  │ DashScope│  │  通义千问  │  │
│  │ 视频转音频│  │  本地ASR │  │  云端ASR │  │  AI总结   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ 阿里OSS  │  │  Notion  │  │   飞书   │  │ Supabase  │  │
│  │  上传    │  │  推送    │  │   推送   │  │  远程DB   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
     ┌──────▼──────┐         ┌────────▼──────┐
     │    Redis    │         │ SQLite/Supabase│
     │  配置持久化  │         │  历史记录存储  │
     │  分类/提示词 │         │               │
     └─────────────┘         └───────────────┘
```

### 组件说明

| 组件 | 作用 | 是否必须 |
|------|------|---------|
| **Redis** | 存所有配置（开关/路径/API Key/分类/提示词） | ✅ 必须 |
| **FFmpeg** | 视频转音频 | ✅ 必须 |
| **FunASR** | 本地语音识别 | ⚡ 使用本地转写时必须 |
| **DashScope** | 百炼云端语音识别 | ⚡ 使用百炼API时必须 |
| **OSS** | 音频/文本云存储 + 为百炼提供公网URL | ⚡ 使用百炼/云存储时必须 |
| **SQLite** | 本地历史记录数据库 | 🔧 开启存储时必须 |
| **Supabase** | 云端历史记录数据库（可替代SQLite） | 🔧 选用时配置 |
| **通义千问** | AI 总结 | 🔧 开启总结时必须 |
| **Notion / 飞书** | 推送转写结果 | 🔧 开启推送时必须 |

---

## 4. 目录结构

```
media2text/                   ← 项目根目录（仓库根）
├── docker-compose.yml           ← Docker 全栈启动配置
├── Makefile                     ← 快捷命令（make up / make dev 等）
├── .env                         ← 你的本地配置（从 .env.example 复制）
├── .env.example                 ← 配置模板（带注释说明）
├── README.md                    ← 项目说明（简要）
├── docs/
│   └── DEPLOYMENT.md            ← 本完整使用手册
│
├── backend/                     ← Python FastAPI 后端
│   ├── main.py                  ← 应用入口，lifespan 启动检查
│   ├── requirements.txt         ← Python 依赖列表
│   ├── Dockerfile               ← 后端 Docker 镜像
│   ├── .dockerignore            ← 构建时排除 .venv、temp 等（勿打进镜像）
│   ├── .env                     ← 后端专属环境变量（可选）
│   ├── media2text.db         ← SQLite 示例文件名（实际路径见 SQLITE_PATH / 设置）
│   ├── temp/                    ← 上传文件临时目录（处理完自动清理）
│   ├── output/                  ← 本地输出根目录
│   │   └── 默认分类/
│   │       ├── audios/          ← 提取的音频文件
│   │       └── captions/        ← 转写文本文件（.md 格式）
│   ├── core/
│   │   ├── logger.py            ← 全链路日志（含 trace_id 追踪）
│   │   ├── redis_client.py      ← Redis 连接单例 + 操作函数
│   │   ├── config_loader.py     ← 从 Redis / 环境变量加载配置
│   │   ├── startup_checks.py    ← 启动时环境自检（FFmpeg / Redis 等）
│   │   └── db_factory.py        ← 数据库引擎工厂
│   ├── models/
│   │   └── schemas.py           ← Pydantic 数据模型
│   ├── routers/
│   │   ├── upload.py            ← 文件上传接口
│   │   ├── process.py           ← 批量处理 + SSE 进度推送
│   │   ├── config.py            ← 配置读写、分类、提示词管理
│   │   ├── history.py           ← 历史记录 CRUD + 导出
│   │   ├── push.py              ← Notion / 飞书推送 API
│   │   ├── integrations.py      ← 集成字段说明（如 /api/integrations/schema）
│   │   └── asr.py               ← FunASR 状态查询 + 按需加载
│   └── services/
│       ├── file_detector.py     ← 文件类型判断
│       ├── video_converter.py   ← FFmpeg 视频→音频
│       ├── oss_uploader.py      ← 阿里云 OSS 上传
│       ├── asr_local.py         ← FunASR 本地推理（单例+状态机）
│       ├── asr_dashscope.py     ← 百炼 API 转写（含结果 URL 二次拉取）
│       ├── markdown_formatter.py ← 转写结果→Markdown 格式
│       ├── summarizer.py        ← AI 总结（可扩展多模型）
│       ├── notion_push.py       ← Notion 推送
│       ├── feishu_push.py       ← 飞书多维表格推送
│       ├── push_common.py       ← 推送共用（字段说明等）
│       ├── integration_payload.py ← 集成导出 / 推送统一字段
│       ├── history_ops.py       ← 历史记录与推送辅助
│       ├── history_export.py    ← 历史记录导出 Excel / CSV
│       ├── db.py                ← 数据库入口（初始化 / 路由用）
│       ├── db_adapter.py        ← 数据库抽象基类
│       ├── db_sqlite.py         ← SQLite 实现
│       ├── db_supabase.py       ← Supabase 实现
│       └── batch_mode_util.py   ← 批量模式显示与存储规范化
│
└── frontend/                    ← Vue3 前端
    ├── package.json
    ├── vite.config.js           ← 开发时代理 /api → localhost:8000
    ├── Dockerfile               ← 前端 Docker 镜像（Nginx 托管）
    ├── nginx.conf               ← Nginx 配置（含 /api 反向代理、单文件上传上限 2G）
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── api/index.js         ← 所有后端 API 调用封装
        ├── stores/
        │   ├── config.js        ← 配置状态（watch + debounce 写 Redis）
        │   ├── files.js         ← 文件列表状态
        │   └── task.js          ← 任务进度状态
        ├── views/
        │   └── Home.vue         ← 三栏主页面
        └── components/
            ├── layout/TopBar.vue
            ├── left/            ← 左侧：上传 + 文件列表
            ├── middle/          ← 中间：配置面板
            ├── right/           ← 右侧：进度 + 结果
            └── modals/          ← 弹窗：设置/历史/提示词管理
```

---

## 5. 环境准备（从零安装）

> 按顺序操作，每步验证通过再继续下一步。

### 5.1 Python 3.11

**为什么是 3.11**：部分依赖（FunASR / PyTorch）在 3.12 存在兼容问题，3.9/3.10 性能略低。

#### Windows

1. 打开：https://www.python.org/downloads/release/python-3119/
2. 下载 **Windows installer (64-bit)**
3. 运行安装，**关键**：勾选底部 **"Add python.exe to PATH"**，然后点 Install Now

```powershell
# 新开 PowerShell 验证
python --version
# 期望输出：Python 3.11.x
```

如果有多个 Python 版本，可以用：

```powershell
py -3.11 --version
```

#### macOS

```bash
# 用 Homebrew（推荐）
brew install python@3.11

# 加入 PATH（只需做一次）
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

python3.11 --version
```

#### Linux（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
python3.11 --version
```

---

### 5.2 创建 Python 虚拟环境并安装依赖

> **为什么要用 venv**：隔离项目依赖，避免污染系统 Python 环境，不同项目互不影响。

```bash
# 进入后端目录
cd media2text/backend

# 创建虚拟环境（只需做一次）
python -m venv .venv

# ── 激活（每次新开终端都需要）──────────────────────────────────
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows CMD:
.venv\Scripts\activate.bat

# macOS / Linux:
source .venv/bin/activate
# ────────────────────────────────────────────────────────────────

# 激活后命令行前缀出现 (.venv)，然后安装依赖
pip install --upgrade pip

# 先装 PyTorch CPU 版（体积约 800MB，必须先装）
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 再装其余依赖
pip install -r requirements.txt
```

> **网络慢/超时？** 加国内镜像参数：
> ```bash
> pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

安装完成验证：

```bash
python -c "import fastapi, funasr, redis, oss2, dashscope; print('✅ 所有依赖安装成功')"
```

---

### 5.3 Node.js 18+ 与前端依赖

```bash
# 验证版本（18.x 或以上即可）
node -v    # 期望：v18.x.x 或 v20.x.x
npm -v
```

如果未安装：去 https://nodejs.org 下载 **LTS 版**，一路安装即可（会自动加入 PATH）。

```bash
# 进入前端目录
cd media2text/frontend

# 安装依赖（只需做一次，package.json 变化后重做）
npm install

# 网络慢时使用国内镜像
npm config set registry https://registry.npmmirror.com
npm install
```

---

### 5.4 FFmpeg

FFmpeg 是处理音视频的命令行工具，**必须安装且在 PATH 中可用**，否则后端启动时会报错并拒绝运行。

#### Windows（详细步骤）

1. 打开：https://www.gyan.dev/ffmpeg/builds/
2. 下载 **ffmpeg-release-essentials.zip**（约 70MB）
3. 解压到固定路径，例如 `C:\ffmpeg\`，解压后目录结构类似：
   ```
   C:\ffmpeg\
   └── ffmpeg-7.x-essentials_build\
       ├── bin\
       │   ├── ffmpeg.exe   ← 这个文件要加入 PATH
       │   ├── ffplay.exe
       │   └── ffprobe.exe
       └── ...
   ```
4. 添加到系统 PATH：
   - 按 `Win + R`，输入 `SystemPropertiesAdvanced`，回车
   - 点「环境变量」→ 在「系统变量」找到 `Path` → 点「编辑」→「新建」
   - 输入 `C:\ffmpeg\ffmpeg-7.x-essentials_build\bin`（换成你的实际路径）
   - 一路确定
5. **新开**一个 PowerShell 窗口验证：

```powershell
ffmpeg -version
# 期望输出首行类似：ffmpeg version 7.x ...
```

#### macOS

```bash
brew install ffmpeg
ffmpeg -version
```

#### Linux

```bash
sudo apt install -y ffmpeg
ffmpeg -version
```

---

### 5.5 Redis

Redis 是本项目**强依赖**，用于存储所有配置。未启动则后端直接拒绝运行。

#### 方式一：Docker 启动（推荐，最简单）

需要先安装 Docker Desktop：https://www.docker.com/products/docker-desktop/

```bash
# 在项目根目录（有 docker-compose.yml 的位置）
docker compose up -d redis

# 验证
docker ps | grep redis
# 看到 redis 容器 running 即可
```

#### 方式二：本机安装 Redis

**macOS**：
```bash
brew install redis
brew services start redis
redis-cli ping   # 返回 PONG 即成功
```

**Linux**：
```bash
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
redis-cli ping
```

**Windows**：
推荐使用 WSL2 安装 Linux 版 Redis，或使用上面的 Docker 方式，Windows 原生没有官方 Redis 安装包。

---

### 5.6 环境验证清单

全部装完后，在**新开的终端**中逐一验证：

```bash
python --version       # Python 3.11.x
node -v                # v18.x.x 或更高
ffmpeg -version        # ffmpeg version 7.x...
redis-cli ping         # PONG（或通过 docker 验证）
docker compose version # Docker Compose version v2.x（如果用 Docker）
```

---

## 6. 配置文件详解

### 6.1 创建 `.env` 文件

```bash
# 在项目根目录
cp .env.example .env   # macOS/Linux
# Windows: 直接复制 .env.example，改名为 .env
```

### 6.2 `.env` 关键配置说明

```bash
# ── Redis ─────────────────────────────────────────────────────
# Redis 连接地址
# 本地开发时（Redis 在本机或 Docker 映射到本机）：
REDIS_URL=redis://127.0.0.1:6379/0
# Docker 全栈模式时（后端和 Redis 都在 Docker 网络里）：
# REDIS_URL=redis://redis:6379/0  ← docker-compose 会自动注入

# ── 数据库 ────────────────────────────────────────────────────
# 选择数据库引擎（sqlite 或 supabase），默认 sqlite
# 注意：这里只是初始默认值，实际以 Redis 中保存的配置为准
DB_ENGINE=sqlite

# SQLite 文件路径（DB_ENGINE=sqlite 时生效）
SQLITE_PATH=./media2text.db

# Supabase 配置（DB_ENGINE=supabase 时填写）
# SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
# SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxx
# SUPABASE_TABLE=records

# ── FunASR ────────────────────────────────────────────────────
# 是否在应用启动后后台预加载 FunASR 模型（true/false）
# true：启动后台异步加载，不阻塞服务启动
# false：首次转写时按需加载（首次会等待约30秒）
PRELOAD_FUNASR=false

# ModelScope 模型缓存目录（FunASR 模型下载位置）
# 默认：~/.cache/modelscope
# 建议指定固定路径，避免重复下载：
# MODELSCOPE_CACHE=/data/modelscope_cache

# ── 本地路径 ──────────────────────────────────────────────────
TEMP_DIR=./temp
OUTPUT_DIR=./output

# ── 跨域（开发时允许所有）────────────────────────────────────
CORS_ORIGINS=*
```

> **注意**：API Key（OSS、DashScope、Notion、飞书、Qwen 等）**不在 `.env` 里配置**，全部在页面「设置」弹窗里填写，保存到 Redis，更安全也更方便。

---

## 7. 启动方式一：纯本地开发模式

> 适合：想修改代码、热重载调试、不使用 Docker

**前提**：Redis 已在运行（Docker 或本机安装均可）

### 第一步：启动后端

```bash
# 新开一个终端，进入 backend 目录
cd media2text/backend

# 激活虚拟环境
source .venv/bin/activate     # macOS/Linux
# 或
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# 启动（热重载模式，修改代码自动重启）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动成功时，你会看到类似日志：

```
INFO     | startup | ✅ FFmpeg 已安装：ffmpeg version 7.0...
INFO     | startup | ✅ Redis 连接成功：redis://127.0.0.1:6379/0
INFO     | startup | ✅ FunASR 已安装（版本：1.x.x）
WARNING  | startup | ⚠️  DashScope API Key 未配置（百炼转写不可用）
WARNING  | startup | ⚠️  OSS 未配置（上传功能不可用）
INFO     | startup | ── 当前配置 ─────────────────────────────
INFO     | startup | 当前分类：默认分类
INFO     | startup | 保存音频到本地：开
INFO     | startup | 转写引擎：本地 FunASR
INFO     | startup | 批量模式：分开输出
INFO     | uvicorn | Application startup complete.
INFO     | uvicorn | Uvicorn running on http://0.0.0.0:8000
```

### 第二步：启动前端

```bash
# 新开另一个终端，进入 frontend 目录
cd media2text/frontend

npm run dev
```

启动成功后会看到：

```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### 第三步：访问页面

打开浏览器，访问：**http://localhost:5173**

---

## 8. 启动方式二：Docker 全栈模式

> 适合：生产部署、一键启动、不想配本地 Python/Node 环境

**前提**：安装了 Docker Desktop（Windows/macOS）或 Docker Engine（Linux）

```bash
# 在项目根目录（有 docker-compose.yml 的位置）

# ── 启动命令 ────────────────────────────────────────────────
# 首次启动（会拉取镜像、构建，需要较长时间）
docker compose up -d --build

# 非首次启动（已构建过镜像，直接启动）
docker compose up -d

# 启动全部服务（等价于 up -d）
make up

# ── 单独启动某个服务 ───────────────────────────────────────
# 仅启动 Redis
docker compose up -d redis

# 仅启动后端（会自动启动依赖的 Redis）
docker compose up -d backend

# 仅启动前端（会自动启动依赖的 backend）
docker compose up -d frontend

# ── 停止命令 ────────────────────────────────────────────────
# 停止全部服务（保留容器和数据卷）
docker compose stop

# 停止并删除全部容器（保留数据卷）
docker compose down

# 停止并删除全部容器 + 数据卷（⚠️ 会丢失所有数据）
docker compose down -v

# ── 单独停止某个服务 ───────────────────────────────────────
# 停止 Redis
docker compose stop redis

# 停止后端
docker compose stop backend

# 停止前端
docker compose stop frontend

# 停止并删除某个容器
docker compose down redis

# ── 重启命令 ────────────────────────────────────────────────
# 重启全部服务
docker compose restart

# 重启单个服务
docker compose restart backend

# ── 重新构建并启动（代码修改后） ───────────────────────────
# 重建全部镜像并启动
# 💡 注意：up -d --build 会自动停止旧容器、重建镜像、启动新容器，无需手动 stop/down
docker compose up -d --build

# 仅重建后端并启动
# 💡 会自动停止 backend 容器，重建镜像，然后启动（Redis 不受影响）
docker compose up -d --build backend

# 仅重建前端并启动（不连带重建 backend）
docker compose up -d --build --no-deps frontend

# 仅重建后端并启动（不连带重建 frontend）
docker compose up -d --build --no-deps backend

# 或使用 Makefile（推荐）
make rebuild-backend     # 重建后端镜像并重启
make rebuild-frontend    # 重建前端镜像并重启

# 或使用 Makefile
make up
```

### 查看启动状态

```bash
docker compose ps
```

期望看到三个服务都是 `running`：

```
NAME                      STATUS
media2text-redis          running
media2text-backend        running
media2text-frontend       running
```

### 查看后端启动日志

```bash
docker compose logs backend
# 或跟随实时日志
docker compose logs -f backend
```

### 访问地址

- **前端**：http://localhost:3000
- **后端 API**：http://localhost:8000
- **API 文档**（FastAPI 自动生成）：http://localhost:8000/docs

### Docker 本地输出路径（重要）

后端跑在 **Linux 容器**里，**不能**在设置里填 Windows 盘符路径（如 `D:\matedata\media-to-text`）。容器不认 `D:\`，文件会写到容器内部，宿主机上的 D 盘和 `backend/output` 都会是空的。

**正确做法：**

1. 在 **设置 → 本地路径与存储** 中，音频/字幕输出根目录填 **`/app/output`**（容器内路径）。
2. 在 `docker-compose.yml` 的 `backend.volumes` 里，把宿主机目录挂到 `/app/output`，例如：

```yaml
volumes:
  - ./backend/output:/app/output
  # Windows 挂 D 盘示例：
  # - D:/matedata/media-to-text:/app/output
```

3. 修改 compose 或路径后执行 `docker compose up -d --build backend` 重建后端。

本地文件结构：`/app/output/{分类}/audios/`、`/app/output/{分类}/captions/`。

> **纯本地开发**（不用 Docker）时，才可以在设置里填 `D:\...` 或 `./output`。

### Makefile 快捷命令一览

```bash
# ── 启动/停止 ─────────────────────────────────────────────
make up                  # 启动全部服务
docker compose up -d     # 同上（原生 Docker 命令）

make down                # 停止全部服务
docker compose down      # 同上

make dev                 # 仅启动 Redis（混合模式开发）
docker compose up -d redis  # 同上

# ── 日志查看 ──────────────────────────────────────────────
make logs                # 查看全部日志（跟随）
docker compose logs -f   # 同上

docker compose logs -f backend    # 仅查看后端日志
docker compose logs -f frontend   # 仅查看前端日志
docker compose logs -f redis      # 仅查看 Redis 日志

# ── 重建镜像 ──────────────────────────────────────────────
make rebuild-backend     # 重建后端镜像并重启
make rebuild-frontend    # 重建前端镜像并重启

docker compose up -d --build backend   # 同上（原生命令）
docker compose up -d --build frontend  # 同上

# ── 其他 ──────────────────────────────────────────────────
docker compose ps        # 查看运行中的容器状态
docker compose down -v   # 停止并删除全部容器和数据卷（⚠️ 数据会丢失）
```

### 注意事项

| 场景 | 说明 |
|------|------|
| 修改后端代码 | 需要 `make rebuild-backend` 重建镜像（无需先停止，会自动处理）|
| 修改前端代码 | 需要 `make rebuild-frontend` 重建镜像（无需先停止，会自动处理）|
| 修改 `frontend/nginx.conf` | 需 **重建** frontend 镜像；`restart` 不会生效（配置在构建时写入镜像）|
| 大文件上传 | Nginx 单文件上限 **2G**；点击「开始处理」时**逐文件上传**，按钮显示 `上传中 (1/N)…` |
| 后端 Docker 构建 | `backend/.dockerignore` 排除本地 `.venv`，避免构建上下文过大 |
| 数据持久化 | SQLite 文件和输出目录通过 volume 挂载到宿主机，数据不丢失 |
| FunASR 模型缓存 | 通过 `funasr_cache` volume 持久化，避免每次重建都重新下载 |
| 修改 `.env` | 需要重启服务 `make down && make up` |
| **重建是否需要先停止？** | **不需要**。`docker compose up -d --build` 会自动停止旧容器、重建、启动新容器 |

---

## 9. 启动方式三：混合模式（推荐日常开发）

> Redis 用 Docker，后端和前端跑在本机 → 可以热重载改代码，又不用本机装 Redis

```bash
# 第一步：仅启动 Redis
make dev
# 或
docker compose up -d redis

# 第二步：终端 A，启动后端（本机，支持热重载）
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 第三步：终端 B，启动前端（本机，Vite 热更新）
cd frontend
npm run dev
```

访问：**http://localhost:5173**

---

## 10. 页面功能详解

### 10.1 整体布局（三栏）

```
┌─────────────────┬──────────────────────┬──────────────────────┐
│   左侧 1/3       │      中间 1/3         │      右侧 1/3         │
│                 │                      │                      │
│  ┌───────────┐  │  当前分类 [默认▼] [+] │  处理进度列表          │
│  │ 分类选择   │  │  ─────────────────   │  （超10条滚动）        │
│  └───────────┘  │  ▌音频存储            │                      │
│                 │  保存本地  ●─         │  ─────────────────    │
│  ┌───────────┐  │  上传OSS   ○─         │                      │
│  │拖拽上传区  │  │  ─────────────────   │  识别结果预览          │
│  │           │  │  ▌转写设置            │  [原文Tab] [总结Tab]  │
│  └───────────┘  │  开启转写  ○─         │                      │
│                 │  保存本地  ○─         │  [复制JSON] [下载]    │
│  ┌───────────┐  │  上传OSS   ○─         │                      │
│  │ 文件列表   │  │  ─────────────────   │                      │
│  │（可滚动）  │  │  ▌批量模式            │                      │
│  │序号 类型   │  │  ●分开 ○合并          │                      │
│  │文件名 大小 │  │  ─────────────────   │                      │
│  │[删除]     │  │  ▌AI总结             │                      │
│  │...        │  │  开启总结  ○─         │                      │
│  └───────────┘  │  ─────────────────   │                      │
│                 │  ▌输出               │                      │
│                 │  推送Notion ○─        │                      │
│                 │  推送飞书   ○─        │                      │
│                 │  存历史记录 ○─        │                      │
│                 │                      │                      │
│                 │  ┌──────────────┐    │                      │
│                 │  │  开始处理    │    │                      │
│                 │  └──────────────┘    │                      │
└─────────────────┴──────────────────────┴──────────────────────┘
```

### 10.2 顶部导航栏

```
🎵 媒体转文本          [历史记录 🕐]  [⚙️ 设置]
```

- **历史记录**：查看所有处理过的记录（需开启「保存到历史记录」开关）
- **⚙️ 设置**：配置转写引擎、OSS、API Key、数据库等不常改的参数

### 10.3 左侧：文件上传

#### 上传操作

1. **拖拽上传**：直接把文件（或多个文件）拖到上传区域松手
2. **点击上传**：点击上传区域，弹出文件选择框，可用 `Ctrl/Cmd + 点击` 多选

> ✅ 支持同时选择多个文件，视频音频可以混合。点击 **「开始处理」** 后按文件**逐个上传**（非一次性打包），列表会显示「上传中 / 已上传 / 失败」；单文件最大 **2GB**（由 `frontend/nginx.conf` 的 `client_max_body_size` 控制）。

支持的格式：
- **视频**：`.mp4` `.mkv` `.avi` `.mov` `.flv` `.wmv` `.webm` `.ts`
- **音频**：`.mp3` `.wav` `.m4a` `.aac` `.ogg` `.flac` `.opus` `.amr` `.wma`

上传后文件列表显示：

```
序号  类型    文件名          状态      大小    操作
1    [视频]  会议录像.mp4    已上传    256MB   [🗑]
2    [音频]  播客ep12.mp3   上传中    45MB    [🗑]
3    [音频]  访谈录音.m4a   —        23MB    [🗑]
                           [清空列表]
```

#### 分类选择

在上传区上方选择分类，文件会保存到对应分类目录：

```
output/
└── 默认分类/
    ├── audios/       ← 音频文件存这里
    └── captions/     ← 转写文本存这里
```

点 **[+ 添加]** 新建分类，分类名不可重复，新建后自动切换到新分类。

### 10.4 中间：处理配置

所有开关**实时保存到 Redis**，下次打开页面自动恢复上次的配置。

#### 配置说明

| 配置项 | 说明 | 注意事项 |
|--------|------|---------|
| **保存音频到本地** | 视频提取的音频（或音频文件）保存到本地 `output/{分类}/audios/` | — |
| **上传音频到 OSS** | 上传音频到阿里云 OSS，获得公网 URL | 需在设置里配好 OSS 参数 |
| **开启转写** | 将音频转为文字 | 关闭则只做视频转音频 |
| **保存文本到本地** | 转写结果保存为 `.md` 文件 | 需先开启「开启转写」 |
| **上传文本到 OSS** | 转写的 `.md` 文件上传 OSS | 需先开启「开启转写」 |
| **批量模式：分开** | 每个文件输出一条记录 | 默认 |
| **批量模式：合并** | 所有文件合并成一条记录 | 需手动填写合并标题 |
| **开启 AI 总结** | 调用大模型生成摘要 | 需先开启「开启转写」，需配置 API Key |
| **推送到 Notion** | 处理完成后自动推送到 Notion 数据库 | 需在设置里配置 Notion Token 和 Database ID |
| **推送到飞书** | 处理完成后自动推送到飞书多维表格 | 需在设置里配置飞书参数 |
| **保存到历史记录** | 结果存入数据库，可在历史记录中查看 | — |

#### 合并模式说明

选择「合并为一条」时，会出现标题输入框：

```
批量模式：○ 分开输出  ● 合并为一条  [输入合并标题...]
```

合并后的文稿格式（Markdown）：

```markdown
# 第一个文件名

第一个文件的转写内容...

---

# 第二个文件名

第二个文件的转写内容...
```

总结时对合并后的全文总结一次（而非每个文件单独总结）。

### 10.5 AI 总结配置

开启「AI 总结」后出现：

```
选择模型：[通义千问 ▼]
选择提示词：[默认总结 ▼]  [💡 管理提示词]
```

点击 **[💡 管理提示词]** 打开提示词管理弹窗：

- **查看**所有提示词（标题 + 内容预览）
- **新增**提示词：填写标题和内容，`{text}` 是转写文本的占位符
- **编辑**已有提示词
- **删除**（「默认总结」不可删除）

内置提示词模板示例：

| 标题 | 适用场景 |
|------|---------|
| 默认总结 | 通用摘要 |
| 会议纪要 | 会议录音，提炼决议和待办 |
| 课程笔记 | 课程视频，整理知识点 |
| 播客精华 | 播客节目，提取金句和观点 |

### 10.6 右侧：结果展示

处理过程中，进度列表实时更新：

```
序号  文件名          当前步骤         进度     状态
1    会议录像.mp4    正在提取音频...   ████░  [处理中]
2    播客ep12.mp3   正在转写音频...   ██░░░  [处理中]
3    访谈录音.m4a   等待处理...       ░░░░░  [等待]
```

处理步骤说明：

| 步骤 | 说明 |
|------|------|
| 检测文件类型 | 判断视频还是音频 |
| 正在提取音频 | FFmpeg 视频→mp3（视频文件才有此步骤）|
| 保存音频到本地 | 复制到 output 目录 |
| 上传音频到 OSS | 上传并获取公网 URL |
| 正在转写音频 | ASR 识别（可能较慢）|
| 上传文本到 OSS | 上传 .md 文件 |
| AI总结中 | 调用大模型 |
| 推送到 Notion | 写入 Notion 数据库 |
| 推送到飞书 | 写入飞书多维表格 |
| ✅ 处理完成 | 全部步骤完成 |

处理完成后，结果在下方展示（分 Tab）：

```
[会议录像]                              字数：2,341字
  [原文 Tab] ──────────────────────────────────────
  # 会议录像
  
  这里是转写的文字内容，带标点符号...
  
  [复制原文]

  [总结 Tab] ──────────────────────────────────────
  ## 核心内容摘要
  
  - 要点一：...
  - 要点二：...
  
  [复制总结]

  🔗 音频链接：https://...oss.../audios/xxx.mp3
  🔗 文本链接：https://...oss.../captions/xxx.md
```

顶部工具栏：**[复制JSON]** **[下载JSON文件]** **[清除结果]**

---

## 11. 输出数据格式说明

所有结果统一输出为 JSON 数组，每个元素格式如下：

```json
[
  {
    "title": "会议录像",
    "source_files": [
      {
        "filename": "会议录像.mp4",
        "audio_oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/默认分类/audios/会议录像.mp3",
        "caption_oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/默认分类/captions/会议录像_transcript.md"
      }
    ],
    "captions": "# 会议录像\n\n这里是转写的内容，带有标点符号...",
    "summary": "## 摘要\n\n- 核心要点一\n- 核心要点二",
    "record_uuid": "a1b2c3d4e5f6789012345678abcdef01"
  }
]
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 文件名（去后缀），合并模式下为手动输入的标题 |
| `source_files` | array | 来源文件列表 |
| `source_files[].filename` | string | 原始文件名 |
| `source_files[].audio_oss_url` | string? | 音频 OSS 公网 URL（开启上传才有值）|
| `source_files[].caption_oss_url` | string? | 文本 OSS 公网 URL（开启上传才有值）|
| `captions` | string | Markdown 格式原文 |
| `summary` | string? | AI 总结内容（开启总结才有值）|
| `record_uuid` | string | 32位 UUID，全局唯一标识 |

### 合并模式的 `captions` 格式

```markdown
# 文件一名称

文件一的转写内容...

---

# 文件二名称

文件二的转写内容...
```

---

## 12. Notion / 飞书集成指南

### 12.1 Notion 集成

#### 第一步：创建 Notion Integration

1. 打开：https://www.notion.so/my-integrations
2. 点 **New integration**
3. 填写名称（如 `media2text`），关联你的工作区
4. 复制 **Internal Integration Token**（格式：`secret_xxxx...`）

#### 第二步：创建 Notion 数据库并授权

1. 在 Notion 中新建一个**全页数据库**（Full Page → Database）
2. 点右上角 **...** → **Connections** → 添加你刚创建的 Integration
3. 从浏览器地址栏复制数据库 ID：

```
https://www.notion.so/你的工作区/【这里就是数据库ID，32位】?v=xxx
```

#### 第三步：手动创建数据库字段

在 Notion 数据库中，按以下顺序创建字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `title` | **Title**（默认已有，改名即可）| 标题 |
| `record_uuid` | Rich Text | 唯一标识 |
| `created_at` | Date | 创建时间 |
| `updated_at` | Date | 更新时间 |
| `category` | Select | 分类 |
| `batch_mode` | Select | 单数据/批数据 |
| `captions` | Rich Text | 原文（Markdown）|
| `summary` | Rich Text | AI总结 |
| `source_files` | Rich Text | 来源文件（JSON）|

> 💡 **快捷方式**：启动后端后，访问 http://localhost:8000/api/integrations/schema，会返回所有需要创建的字段和类型，同时在启动日志里也会打印一次。

#### 第四步：在设置中填写配置

点页面右上角 **⚙️ 设置** → 找到 Notion 配置：

```
Notion Token:       [secret_xxxxxxxxxxxxx]
Database ID:        [a1b2c3d4e5f67890abcdef1234567890]  ← 32位无连字符
```

> ⚠️ **常见错误**：Database ID 必须是 32 位 UUID，不能填数据库名称。

---

### 12.2 飞书集成

#### 第一步：创建飞书应用

1. 打开：https://open.feishu.cn/
2. 进入「开发者后台」→「创建应用」
3. 填写应用名称，创建完成后记录 **App ID** 和 **App Secret**
4. 在「权限管理」中开启：
   - `bitable:app`（多维表格读写权限）

#### 第二步：创建飞书多维表格

1. 在飞书中新建一个**多维表格**
2. 从 URL 中获取 **App Token**：
   ```
   https://feishu.cn/base/【App Token 在这里】?table=tblXXXX
   ```
3. 从 URL 中获取 **Table ID**：
   ```
   https://feishu.cn/base/xxx?table=【Table ID 在这里】
   ```
4. 将应用添加到多维表格的协作者（点右上角「...」→「添加文档应用」）

#### 第三步：手动创建字段

在飞书多维表格中创建以下字段：

| 字段名 | 飞书类型 | 说明 |
|--------|---------|------|
| `title` | 文本（主字段） | 标题 |
| `record_uuid` | 文本 | 唯一标识 |
| `created_at` | 日期时间 | 创建时间 |
| `updated_at` | 日期时间 | 更新时间 |
| `category` | 单选 | 分类 |
| `batch_mode` | 单选 | 单数据/批数据 |
| `captions` | 文本 | 原文 |
| `summary` | 文本 | AI总结 |
| `source_files` | 文本 | 来源文件 |

#### 第四步：在设置中填写配置

```
飞书 App ID:         [cli_xxxxxxxxxxxx]
飞书 App Secret:     [xxxxxxxxxxxxxxxxxxxxxx]
Bitable App Token:  [Hxxxxxxxxxxxxxxxxxxxxxx]
Table ID:           [tblxxxxxxxxxxxxxx]
```

---

## 13. OSS 配置指南

### 13.1 为什么需要 OSS

| 需求 | 是否需要 OSS |
|------|------------|
| 使用本地 FunASR 转写 | ❌ 不需要 |
| 使用阿里云百炼 API 转写 | ✅ **必须**（百炼只接受公网 URL）|
| 音频/文本云端备份 | ✅ 需要 |
| 在 Notion/飞书 里显示音频链接 | ✅ 需要 |

### 13.2 获取 OSS 配置参数

1. 登录阿里云控制台：https://oss.console.aliyun.com
2. 创建 Bucket（选你最近的地域，如 `华东1（杭州）`）
3. 将 Bucket 的**读权限**设为「公共读」（这样百炼 API 才能访问）
4. 进入「访问控制 RAM」创建子账号，赋予 OSS 读写权限，生成 **AccessKey ID** 和 **AccessKey Secret**

### 13.3 在设置中填写

```
Access Key ID:      [LTAI5xxxxxxxxxxxxxxxxxx]
Access Key Secret:  [xxxxxxxxxxxxxxxxxxxxxxxxxxxx]
Bucket Name:        [your-bucket-name]
Endpoint:           [oss-cn-hangzhou.aliyuncs.com]
```

Endpoint 常用值：

| 地域 | Endpoint |
|------|---------|
| 华东1（杭州）| `oss-cn-hangzhou.aliyuncs.com` |
| 华东2（上海）| `oss-cn-shanghai.aliyuncs.com` |
| 华北2（北京）| `oss-cn-beijing.aliyuncs.com` |
| 华南1（深圳）| `oss-cn-shenzhen.aliyuncs.com` |

填写完成后点 **[测试连接]** 验证是否配置正确。

### 13.4 网络失败与自动重试

OSS 上传与转写（FunASR / 百炼）失败时会 **自动重试最多 3 次**（间隔 1s、2s）。实现见 `backend/core/retry.py`，测试见 `backend/tests/test_retry.py`。

---

## 14. 历史记录与二次处理

### 14.0 导出当前批次识别结果（无需入库）

整批任务全部结束后，右侧 **「识别结果」** 才显示列表。可用 **下载全部** 导出 JSON（`captions` 为转写正文）；先下载再点 **清除**，避免刷新后丢失。长期留存请开 **保存到历史记录** 或 **保存文本到本地**。

### 14.1 查看历史记录

点顶部 **[历史记录 🕐]** 打开弹窗。

**前提**：处理文件时开启了「保存到历史记录」开关。

### 14.2 历史列表

```
[多选框] UUID      时间           分类    标题        模式    原文(截断)  文本OSS       AI总结       Notion       飞书        操作
[□]    a1b2c3d4  2025-04-24    默认    会议录像    单数据  这是内容... 已上传|[上传]  已总结|[总结] 已推送|[推送] 未推送|[推送] [查看][复制]
[□]    e5f6g7h8  2025-04-23    会议    产品讨论    批数据  讨论了...   未上传|[上传]  未总结|[总结] 未推送|[推送] 未推送|[推送] [查看][复制]
```

顶部操作栏：

```
[批量删除]  [清空历史]  [导出Excel（选中/全部）]
```

### 14.3 二次处理（重要功能）

所有操作按钮**永远显示**，可以重复点击：

| 按钮 | 已处理时 | 动作 |
|------|---------|------|
| **上传** | 状态显示「已上传」| 重新上传，覆盖 OSS 原文件 |
| **总结** | 状态显示「已总结」| 重新调用大模型，覆盖原总结 |
| **推送（Notion）** | 状态显示「已推送」| 根据 UUID 在 Notion 中更新记录 |
| **推送（飞书）** | 状态显示「已推送」| 根据 UUID 在飞书中更新记录 |

### 14.4 查看详情

点 **[查看]** 按钮打开详情弹窗：

```
┌─────────────────── 记录详情 ────────────────────────┐
│  来源文件                                            │
│  ┌────────────────────────────────────────────┐    │
│  │ 会议录像.mp4                                │    │
│  │ [▶ 播放音频]  [🔗 文本链接]  [📋 复制链接]  │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  原文（2,341字）                    [📋 复制原文]   │
│  ┌────────────────────────────────────────────┐    │
│  │ # 会议录像                                  │    │
│  │                                             │    │
│  │ 这里是转写的文字内容...                     │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  总结                              [📋 复制总结]   │
│  ┌────────────────────────────────────────────┐    │
│  │ ## 摘要                                     │    │
│  │ - 要点一：...                               │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### 14.5 导出 Excel

支持导出选中记录或全部记录为 Excel 文件，字段按以下顺序：

`record_uuid` → `created_at` → `updated_at` → `title` → `category` → `batch_mode` → `captions` → `summary` → `source_files`

---

## 15. 常见问题与排查

### 15.1 后端启动相关

**Q: 后端启动时报 `FFmpeg not found`**

```
ERROR | startup | ❌ FFmpeg 未安装，请按以下步骤安装：
Windows: 下载 https://www.gyan.dev/ffmpeg/builds/ 并加入 PATH
macOS: brew install ffmpeg
Linux: sudo apt install ffmpeg
```

→ 按提示安装 FFmpeg，然后**新开终端**再启动后端（PATH 变化需要新终端才生效）

---

**Q: 后端启动时报 Redis 连接失败**

```
ERROR | startup | ❌ Redis 连接失败：redis://127.0.0.1:6379/0
请启动 Redis，可使用 Docker：docker compose up -d redis
```

→ 确认 Redis 是否运行：`redis-cli ping`，应返回 `PONG`；检查 `.env` 中 `REDIS_URL` 是否正确

---

**Q: FunASR 模型首次下载很慢**

→ 模型需从 ModelScope 下载（约 500MB）。可以：
1. 等待下载完成（只需一次，缓存在 `~/.cache/modelscope/`）
2. 如果网络不好，设置环境变量使用镜像：
   ```bash
   export MODELSCOPE_ENVIRONMENT=CN
   ```
3. 临时改用百炼 API，等网络好时再切回本地

---

**Q: 前端启动后访问显示空白页面**

→ 检查：
1. 后端是否正常运行（访问 http://localhost:8000/docs 是否能打开）
2. `vite.config.js` 中代理配置是否正确（`/api` → `http://localhost:8000`）
3. 浏览器控制台（F12）是否有报错

---

### 15.2 转写相关

**Q: 百炼 API 转写失败，返回"无文本内容"**

最常见原因：OSS Bucket 未设置公共读权限，百炼无法访问音频文件。

检查步骤：
1. 登录阿里云 OSS 控制台
2. 进入 Bucket → 权限管理 → Bucket ACL
3. 确认读写权限为「公共读」
4. 复制一个已上传音频的 URL，在浏览器中直接访问，能下载则权限正确

---

**Q: 百炼 API 返回有数据但 chars=0**

→ 这是结果解析问题。百炼 API 返回的是一个 `transcription_url`（结果文件的下载链接），真正的文字在这个链接的 JSON 文件里，需要二次 GET 请求才能拿到。

检查后端日志，如果看到类似：
```
INFO | asr_dashscope | task_id=xxx status=SUCCEEDED
INFO | asr_dashscope | chars=0
```

→ 说明没有正确拉取 `transcription_url`，检查 `asr_dashscope.py` 中是否有 GET 下载 JSON 并解析 `transcripts[0].text` 的逻辑

---

**Q: FunASR 转写结果没有标点符号**

→ 检查 `asr_local.py` 中模型初始化是否包含 `punc_model="ct-punc"`：

```python
# 示例代码（仅供参考，实际代码在 backend/services/asr_local.py 中）
from funasr import AutoModel

model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",   # ← 这行不能少
    device="cpu"
)
```

---

**Q: FunASR 转写很慢**

R7 6800H CPU 的大致速度参考：

| 音频时长 | 大约转写时间 |
|---------|------------|
| 10 分钟 | 2~5 分钟 |
| 30 分钟 | 5~15 分钟 |
| 1 小时 | 10~30 分钟 |

→ 这是正常现象，CPU 推理比 GPU 慢约 5~10 倍。如果需要更快速度，考虑使用百炼 API。

---

### 15.3 Notion / 飞书相关

**Q: Notion 推送报错 `body.parent.database_id should be a valid uuid`**

→ Database ID 填写错误。正确的 ID 是 32 位纯 hex 字符，从 Notion 数据库页面 URL 中复制：

```
https://notion.so/workspace/【32位ID在这里，不包含 ? 后面的部分】?v=xxx
```

注意：只取 `?` 前面的那 32 位，不含 `-`（系统会自动转换格式）

---

**Q: Notion 推送报错 401 Unauthorized**

→ Token 填写错误，或者数据库没有给这个 Integration 授权。

检查：在 Notion 数据库页面 → 右上角 `...` → `Connections` → 确认你的 Integration 在列表中

---

**Q: 飞书推送成功但多维表格里看不到数据**

→ 检查：
1. 应用是否已添加到多维表格协作者（点右上角「...」→「添加文档应用」→ 选你的应用）
2. App Token 和 Table ID 是否正确（从 URL 复制，区分大小写）
3. 字段名称是否与推送的 key 完全一致

---

### 15.4 Docker 相关

**Q: Docker 全栈模式，后端连不上 Redis**

→ 检查 `docker-compose.yml` 中后端的环境变量是否设置了 `REDIS_URL=redis://redis:6379/0`（注意不是 `127.0.0.1`，在 Docker 网络里 Redis 服务名是 `redis`）

---

**Q: 修改了代码，但 Docker 里没有生效**

→ Docker 打包时会 build 镜像，修改代码后需要重建：

```bash
make rebuild-backend   # 重建后端
make rebuild-frontend  # 重建前端
```

---

**Q: FunASR 模型在 Docker 里每次重启都要重新下载**

→ 检查 `docker-compose.yml` 中是否有 volume 挂载模型缓存：

```yaml
volumes:
  - funasr_cache:/root/.cache  # 这行必须存在
```

---

**Q: Docker 部署，D 盘或 `backend/output` 里没有文件**

→ 设置里勿填 `D:\...`，除非已在 compose 将宿主机目录挂载到 `/app/output`；输出根目录应填 `/app/output`。详见 §8「Docker 本地输出路径」。

---

**Q: OSS 上传报 SSL / 连接被重置**

→ 项目已自动重试 3 次；仍失败请检查网络/VPN，或在设置中测试 OSS 连接。

---

## 16. 性能参考与建议

### 硬件配置参考（R7 6800H + 32GB 内存）

| 场景 | 配置建议 | 预计速度 |
|------|---------|---------|
| 日常少量转写 | FunASR 本地，PRELOAD_FUNASR=false | 首次慢30秒加载，后续正常 |
| 批量处理（每天数小时音频）| FunASR 本地，PRELOAD_FUNASR=true | 无加载等待 |
| 对速度要求高 | 百炼 API（需 OSS）| 云端处理，速度快 |
| 隐私数据 | FunASR 本地，不开 OSS/Notion/飞书 | 数据不出本地 |

### 建议的工作流

**场景一：处理会议录音，存飞书**
1. 设置弹窗：配置飞书参数
2. 主页开关：开启转写 + 开启总结 + 推送飞书 + 存历史记录
3. 提示词选择：会议纪要
4. 批量上传所有录音文件 → 开始处理

**场景二：批量处理课程视频，本地存档**
1. 主页开关：保存音频到本地 + 开启转写 + 保存文本到本地
2. 批量模式：分开输出
3. 上传所有视频文件 → 开始处理
4. 结果保存在 `output/默认分类/` 下

**场景三：处理敏感会议，数据不出内网**
1. 不配置 OSS、不配置 Notion/飞书、不使用百炼 API
2. 转写引擎选本地 FunASR
3. 开启保存本地 + 存历史记录
4. 一切数据留在本机

---

*如遇文档与实际代码不一致，以代码和启动日志为准。欢迎提 Issue 反馈问题。*