# MyAgent Desktop Pet

MyAgent Desktop Pet 是一个本地优先的 AI 个人桌面宠物项目。它不是单纯的聊天页面，而是把本地大模型、RAG 私有知识库、MCP 工具调用、任务管理、用户画像、长期陪伴记忆、每日总结和 Electron 桌面端整合在一起，形成一个可以长期陪伴、可以主动提醒、也可以在权限确认后执行本地动作的桌面智能体。

项目整体由你独立完成，适合作为个人 AI Agent / 桌面宠物 / 本地知识库助手方向的综合作品。

## 项目亮点

- 使用 FastAPI 设计后端接口，覆盖聊天、会话历史、知识库、任务、用户画像、健康检查、设置、日志、MCP、行动队列、每日总结等模块。
- 基于 LangChain ReAct Agent 构建智能体执行链，支持根据用户意图调用本地知识库检索、联网搜索、天气查询、文档总结、任务管理、用户画像更新和 MCP 工具。
- 搭建 RAG 知识库流程，支持 PDF、TXT、MD 文件上传，完成文本加载、切分、元数据补充、文档去重、Qdrant 向量化存储和 MMR 检索。
- 集成本地 Ollama 模型和 `BAAI/bge-small-zh-v1.5` Embedding，实现离线问答和私有资料检索增强。
- 支持多模态文档处理，使用 PyMuPDF 提取 PDF 图片，结合 RapidOCR 和本地视觉模型对图片内容进行识别与语义描述。
- 设计桌宠状态机，让宠物根据聊天、思考、执行、提醒、错误、等待授权等状态展示不同表情和行为。
- 设计长期陪伴系统，支持会话裁剪、会话摘要、用户画像、任务清单、每日总结、主动提醒、陪伴等级、亲密度和近期互动记录。
- 接入 MCP 工具网关，并通过 action queue 权限确认机制控制文件创建、文件修改、任务更新等高风险动作。
- 使用 Vue 3 + Vite 构建前端控制台，支持聊天、Markdown 渲染、图片粘贴上传、知识库管理、任务展示、用户画像展示、MCP 状态展示、日志查看和设置页面。
- 使用 Electron 封装为 Windows 桌面应用，支持主控制台、悬浮桌宠窗口、系统托盘、自启动配置和安装包打包。

## 技术栈

### 后端

- Python
- FastAPI
- LangChain / LangChain Core / LangChain Community
- LangChain Ollama
- LangChain Qdrant
- Qdrant 本地向量库
- Sentence Transformers
- HuggingFace Embeddings
- PyMuPDF
- PDFPlumber
- RapidOCR
- MCP Python SDK

### 前端与桌面端

- Vue 3
- Vite
- Axios
- Marked
- DOMPurify
- Electron
- Electron Builder

### 本地模型

- Ollama 文本模型：默认示例为 `gemma4:e4b`
- Ollama 视觉模型：默认示例为 `qwen3-vl:8b`
- Embedding：默认示例为 `BAAI/bge-small-zh-v1.5`

模型名称可以在 `.env` 或设置页面中调整。

## 整体架构

```text
用户
  │
  ▼
Electron 桌面应用
  ├─ Vue 控制台
  ├─ 悬浮桌宠窗口
  ├─ 托盘与自启动
  └─ 后端进程管理
        │
        ▼
FastAPI 后端
  ├─ Chat API
  ├─ Knowledge API
  ├─ Task API
  ├─ Profile API
  ├─ Pet State API
  ├─ Daily Report API
  ├─ Settings API
  ├─ MCP API
  └─ Action Queue API
        │
        ▼
Agent 执行层
  ├─ LangChain ReAct Agent
  ├─ 工具路由
  ├─ 本地知识库检索
  ├─ 联网搜索
  ├─ 天气查询
  ├─ 文档总结
  ├─ 任务工具
  ├─ 用户画像工具
  └─ MCP 工具
        │
        ▼
本地能力层
  ├─ Ollama LLM
  ├─ Ollama Vision Model
  ├─ HuggingFace Embedding
  ├─ Qdrant Vector Store
  ├─ JSON 持久化记忆
  └─ 本地 MCP Server
```

## 目录结构

```text
.
├── action_queue/        # 行动队列与权限确认机制
├── agent/               # Agent 构建、路由、提示词、执行入口
├── config/              # 项目配置、设置读写、MCP 配置模板
├── core/                # LLM、Embedding、向量库、健康检查、日志工具
├── knowledge/           # 文档加载、OCR、切分、元数据、入库、检索
├── mcp_bridge/          # MCP 管理器、LangChain 工具适配器、本地 MCP Server
├── memory/              # 聊天历史、会话摘要、长期记忆、用户画像、任务
├── pet/                 # 桌宠状态机、陪伴系统、每日总结
├── tools/               # Agent 可调用的本地工具
├── frontend/            # Vue 前端与 Electron 桌面壳
├── main.py              # FastAPI 后端入口
├── api_models.py        # API 请求和响应模型
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
└── README.md            # 项目说明文档
```

## 核心模块说明

### 1. FastAPI 后端

后端入口是 `main.py`，主要提供以下接口能力：

- `/api/chat`：聊天接口，连接 Agent 执行链。
- `/api/chat/history`：获取会话历史。
- `/api/chat/clear`：清空当前会话。
- `/api/knowledge`：查看知识库文档列表。
- `/api/knowledge/upload`：上传 PDF、TXT、MD 文件并入库。
- `/api/knowledge/{doc_id}`：删除知识库文档。
- `/api/tasks`：查看和管理任务清单。
- `/api/profile`：查看用户画像。
- `/api/pet/state`：获取桌宠当前状态。
- `/api/pet/event`：触发桌宠状态事件。
- `/api/mcp/status`：查看 MCP 网关状态。
- `/api/mcp/tools`：查看 MCP 工具列表。
- `/api/mcp/call`：调用 MCP 工具。
- `/api/actions`：查看待授权动作。
- `/api/actions/{id}/approve`：批准并执行动作。
- `/api/actions/{id}/reject`：拒绝动作。
- `/api/daily-report/today`：读取今日总结。
- `/api/daily-report/generate`：生成每日总结。
- `/api/settings`：读取和保存模型、MCP、知识库、桌宠偏好设置。
- `/health/live`：进程存活检查。
- `/health/ready`：服务就绪检查。

### 2. Agent 执行链

Agent 位于 `agent/` 目录中，主要负责：

- 判断用户输入属于普通聊天、本地知识库、联网搜索等哪类场景。
- 根据路由结果构建对应工具集合。
- 使用 LangChain ReAct Agent 进行推理和工具调用。
- 在必要时调用 RAG 检索、联网搜索、天气、任务、用户画像、MCP 等工具。
- 结合短期会话历史和长期记忆生成最终回答。

### 3. RAG 知识库

知识库相关代码位于 `knowledge/` 目录中，流程包括：

1. 接收用户上传文件。
2. 根据文件类型使用对应 loader 加载内容。
3. PDF 文件可提取图片并执行 OCR。
4. 对文本进行切分。
5. 补充 source、file hash、chunk id、页码等元数据。
6. 检查是否重复导入。
7. 写入 Qdrant 本地向量库。
8. 使用 MMR 检索返回相关内容。

默认支持文件类型：

- `.pdf`
- `.txt`
- `.md`

### 4. 多模态文档处理

项目不仅能读取 PDF 文本，还能处理 PDF 中的图片：

- 使用 PyMuPDF 提取 PDF 图片。
- 使用 RapidOCR 识别图片中的文字。
- 使用 Ollama 视觉模型对图片做语义描述。
- 将 OCR 结果和视觉描述合并到文档内容中，增强后续检索效果。

这使得项目可以处理截图、流程图、表格图片、架构图等更复杂的资料。

### 5. 记忆与陪伴系统

记忆相关代码位于 `memory/` 和 `pet/` 目录中，包含：

- 会话历史管理。
- 短期上下文裁剪。
- 会话摘要。
- 用户画像持久化。
- 任务清单管理。
- 长期记忆向量检索。
- 桌宠状态持久化。
- 陪伴天数、亲密度、等级、打卡记录。
- 每日总结和明日建议。

桌宠不只是显示一个形象，而是会根据用户互动持续积累状态和记忆。

### 6. MCP 工具网关

MCP 相关代码位于 `mcp_bridge/` 目录中。

项目当前支持：

- 读取项目文件。
- 搜索项目文本。
- 获取项目概览。
- 创建目录。
- 创建文件。
- 追加文件内容。
- 替换文件文本。
- 记录 Agent 笔记。
- 创建 Skill 草稿。
- 查看知识库文档。
- 查看任务列表。
- 添加任务。
- 更新任务状态。
- 获取用户画像摘要。
- 获取桌宠状态快照。

其中涉及写文件、改文件、更新任务等动作，会先进入 action queue，等待用户在前端批准后再执行。

## 环境要求

建议环境：

- Windows 10 / Windows 11
- Python 3.10 或更高版本
- Node.js 18 或更高版本
- Git
- Ollama

如果要使用 GPU 加速 Embedding，需要正确安装支持 CUDA 的 PyTorch。否则可以使用 CPU 模式，首次启动更稳。

## 初始化项目

### 1. 克隆仓库

```powershell
git clone <你的仓库地址>
cd MyAgent
```

### 2. 创建本地配置

```powershell
Copy-Item .env.example .env
Copy-Item config\mcp_servers.example.json config\mcp_servers.json
```

然后根据自己的机器修改 `.env`：

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
OLLAMA_VISION_MODEL=qwen3-vl:8b
EMBEDDING_DEVICE=cpu
```

如果你已经正确配置 CUDA，可以改为：

```env
EMBEDDING_DEVICE=cuda
```

### 3. 创建 Python 虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 4. 安装后端依赖

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果你需要安装指定 CUDA 版本的 PyTorch，请参考 PyTorch 官网命令，先安装匹配你显卡和 CUDA 版本的 `torch`，再安装其余依赖。

### 5. 安装前端依赖

```powershell
cd frontend
npm install
```

### 6. 准备 Ollama 模型

确保 Ollama 已经启动，然后拉取模型：

```powershell
ollama pull gemma4:e4b
ollama pull qwen3-vl:8b
```

如果你使用其他模型，记得同步修改 `.env` 中的模型名称。

## 启动方式

### 方式一：单独启动后端

在项目根目录执行：

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

启动后可以访问：

- `http://127.0.0.1:8000/health/live`
- `http://127.0.0.1:8000/health/ready`

第一次启动可能较慢，因为会初始化：

- Embedding 模型
- Qdrant 向量库
- Retriever
- Agent Executor
- Ollama LLM
- MCP 工具

### 方式二：启动前端开发服务

在 `frontend/` 目录执行：

```powershell
npm run dev
```

这只会启动浏览器中的前端页面，不会自动启动 FastAPI 后端。

### 方式三：启动 Electron 桌面端

在 `frontend/` 目录执行：

```powershell
npm run desktop
```

这个命令会：

1. 构建前端页面。
2. 启动 Electron 桌面壳。
3. 检查 `127.0.0.1:8000` 是否已有后端。
4. 如果没有后端，则尝试自动启动 FastAPI。

如果你想让 Electron 使用指定 Python，可以设置：

```powershell
$env:MYAGENT_PYTHON="D:\your\python.exe"
npm run desktop
```

### 方式四：开发模式下启动 Electron

先启动 Vite：

```powershell
cd frontend
npm run dev
```

再开一个终端执行：

```powershell
npm run desktop:dev
```

## 打包 Windows 安装包

在 `frontend/` 目录执行：

```powershell
npm run desktop:build
```

打包完成后，安装包会生成在：

```text
frontend/release/
```

该目录已经被 `.gitignore` 忽略，不会上传到 GitHub。

## 常见问题

### 1. 打开桌面端后一开始显示 Offline

这通常不是前端坏了，而是后端还在初始化。首次启动时，Embedding、Qdrant、Agent 和 Ollama 初始化可能需要几十秒。

可以查看：

```text
logs/electron-backend.log
```

或在前端设置页查看最近日志。

### 2. HuggingFace Embedding 下载失败

可能原因：

- 网络无法访问 HuggingFace。
- 模型没有完整下载到本地缓存。
- 没有配置代理或镜像。
- 第一次启动时下载超时。

可以尝试：

- 提前手动下载 `BAAI/bge-small-zh-v1.5`。
- 设置 HuggingFace Token。
- 使用可访问的镜像源。
- 暂时将 `EMBEDDING_DEVICE=cpu`，先保证项目跑通。

### 3. Ollama 模型不可用

确认 Ollama 正在运行：

```powershell
ollama list
```

确认 `.env` 中模型名和本地模型名一致：

```env
OLLAMA_MODEL=gemma4:e4b
OLLAMA_VISION_MODEL=qwen3-vl:8b
```

### 4. MCP 工具不能调用

请检查：

- 是否安装了 `mcp` Python 包。
- `config/mcp_servers.json` 是否存在。
- `command` 是否指向正确 Python。
- `cwd` 是否指向项目根目录。

可以先从示例复制：

```powershell
Copy-Item config\mcp_servers.example.json config\mcp_servers.json
```

再按本机路径调整。

## GitHub 上传说明

本项目已经配置 `.gitignore`，以下内容不应该上传：

- `.env`
- `.venv/`
- `data/`
- `logs/`
- `temp/`
- `local_qdrant/`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/release/`
- `config/mcp_servers.json`

应该上传：

- 源码目录
- `requirements.txt`
- `frontend/package.json`
- `frontend/package-lock.json`
- `.env.example`
- `config/mcp_servers.example.json`
- `.gitignore`
- `README.md`

初始化仓库后可以执行：

```powershell
git status --short
```

如果看到 `.env`、`.venv`、`data`、`logs`、`node_modules`、`release` 等文件出现在待提交列表里，说明忽略规则没有生效，需要先停下来检查。

## 推荐提交命令

```powershell
git init
git add .
git status
git commit -m "Initial commit"
git branch -M main
git remote add origin <你的 GitHub 仓库地址>
git push -u origin main
```

## 项目定位总结

这个项目可以概括为：

一个基于本地大模型、私有知识库、MCP 工具调用和长期陪伴记忆的个人桌面宠物 Agent。它既能作为本地资料问答助手，也能作为任务陪伴工具，还能在权限确认后执行文件创建、任务更新等本地动作。

相比普通聊天机器人，本项目更强调：

- 本地化与隐私性
- 桌面陪伴感
- 知识库增强
- 长期记忆
- 工具执行能力
- 权限确认与安全边界
- Electron 桌面产品化
