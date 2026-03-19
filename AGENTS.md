# AGENTS.md - 本地开发指南

## 环境搭建

### 前置条件

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.10 | 运行主程序 |
| pip | 最新 | 包管理 |
| Node.js | >= 18 | 前端开发 + MCP Server 运行时 |

### 初始化步骤

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2. 安装项目（开发模式）
pip install -e .

# 3. 安装前端依赖
cd web
npm install
cd ..

# 4. 验证安装
python index.py
```

## 项目架构

```
index.py  →  lib/agent.py (主循环)
                ├── lib/api.py            (LLM API 通信)
                ├── lib/tools.py          (工具注册 & 分发)
                ├── lib/workbench_state.py (组织架构 & 任务状态)
                ├── lib/dashboard_server.py (REST API 服务)
                ├── lib/ui.py             (终端渲染)
                └── lib/config.py         (配置)

web/       →  React 前端 (Vite + TypeScript)
                ├── src/App.tsx          (主页面)
                ├── src/api.ts           (API 客户端)
                └── src/components/      (UI 组件)
```

## 组织架构

**用户固定为老板角色**，CLI 的所有输入都会发给 CTO 处理。

```
老板 (用户) ─── 下达指令 / 闲聊
    │
    ▼
CTO ─────────── 判断：任务 or 闲聊？
    │
    ├─ 闲聊 → 直接回复老板
    │
    └─ 任务 → 创建任务 → 询问员工 → 分配 → 执行 → 验收对齐 → 更新状态 → 待确认
          │
          ▼
       员工 (Worker) ─ 执行具体任务，每人负责一个项目目录
```

### 任务流程

1. **老板下达指令** → CLI 输入发给 CTO
2. **CTO 判断**：
   - 闲聊（问候、咨询）→ 直接回复
   - 任务（具体工作）→ 进入任务流程
3. **任务流程**：
   - CTO 调用 `create_task` 创建任务
   - CTO 调用 `ask_worker(task_id=...)` 询问相关员工
   - 员工回复是否相关（自动写入任务 conversation）
   - CTO 必须继续 `ask_worker(task_id=...)` 做方案/风险/依赖讨论（至少一轮）
   - 讨论完成后，CTO 调用 `add_subtask` 分配子任务
   - 员工执行任务
   - CTO 调用 `update_subtask` 更新状态
   - **验收对齐**：所有子任务完成后，CTO 必须用 `ask_worker` 逐一与相关员工确认执行结果是否符合方案
   - 验收通过后，CTO 调用 `update_task(status="pending_confirmation")`
   - 老板调用 `/confirm <任务ID>` 确认完成

### 任务状态流转

```
pending → analyzing → assigned → running → pending_confirmation → completed
                                                      ↓
                                                  cancelled
```

- **pending**: 待处理
- **analyzing**: 分析中
- **assigned**: 已分配
- **running**: 进行中
- **pending_confirmation**: 等待老板确认
- **completed**: 已完成
- **cancelled**: 已取消

### CLI 命令

| 命令 | 说明 |
|------|------|
| `/tasks` | 查看任务列表 |
| `/task <任务ID或标题>` | 查看任务详情 |
| `/confirm <任务ID>` | 确认完成任务 |
| `/roles` | 查看组织架构 |
| `/status` | 查看当前状态（含待确认任务） |
| `/dashboard` | 打开 Web 配置页面 |

### CTO 工具

**CTO 只负责分配任务，不执行具体工作。** 所有具体工作必须派发给员工。

CTO 可调用以下工具管理任务：

| 工具 | 说明 |
|------|------|
| `create_task` | 创建任务 |
| `update_task` | 更新任务状态和总结 |
| `add_subtask` | 添加子任务，分配给员工 |
| `update_subtask` | 更新子任务状态 |
| `ask_worker` | 询问/指派员工工作 |
| `list_workers` | 列出所有员工 |
| `log_conversation` | 记录对话日志 |
| `get_task_status` | 获取任务详情 |

**CTO 不能使用的工具**（只能由员工使用）：
- 文件操作：`read`、`write`、`edit`、`glob`、`grep`、`fs`
- 命令执行：`bash`
- 网络请求：`search`、`browse`
- MCP 工具

### 员工工作模式

员工（Worker）支持两种工作模式：

#### 1. LLM API 模式（默认）
- 调用配置的 LLM API 获取回复
- 适合简单问答、信息收集
- 需要配置 `api_key`、`model`、`api_url`

#### 2. Claude CLI 模式
- 直接调用 `claude` 命令在项目目录执行任务
- Claude Code 会自动处理文件读写、代码修改等
- 执行完成后返回结果摘要
- 适合实际开发工作

**权限审批机制**（Claude CLI 模式）：

当 `CLAUDE_SKIP_PERMISSIONS=false`（默认），员工执行涉及文件写入的任务时：
1. 系统自动创建权限审批请求
2. 老板在 Web Dashboard → **权限审批** 页面查看并确认
3. 批准后系统自动带 `--dangerously-skip-permissions` 执行
4. 拒绝则任务中止

如需跳过审批（自动执行），设置环境变量：`CLAUDE_SKIP_PERMISSIONS=true`

| API 端点 | 方法 | 说明 |
|----------|------|------|
| `/api/approvals` | GET | 审批列表 |
| `/api/approvals/:id/approve` | POST | 批准审批 |
| `/api/approvals/:id/reject` | POST | 拒绝审批 |

**启用 Claude CLI 模式**：在员工配置中设置 `"use_claude_cli": true`

```python
# Claude CLI 模式员工示例
{
  "id": "worker-001",
  "type": "worker",
  "name": "前端开发",
  "project_path": "D:/work/frontend",
  "use_claude_cli": true,  # 启用 Claude CLI
  "rules": ["先理解现有代码再修改"]
}
```

**前置条件**：
- 已安装 Claude CLI (`npm install -g @anthropic-ai/claude-code`)
- 已配置 `ANTHROPIC_API_KEY` 环境变量

### 数据模型

```python
# 角色数据结构
{
  "id": "role-xxx",
  "type": "boss | cto | worker",
  "name": "前端组-张三",
  "project_path": "D:/work/my-project",  # 仅 worker 使用
  "rules": ["修改前先读 README", "只在项目目录内工作"],
  "context": "技术栈: React + TypeScript...",
  "api_key": "sk-...",           # 每个角色独立配置
  "system_prompt": "...",        # 自定义 prompt
  "model": "claude-3-5-sonnet",
  "use_claude_cli": true         # 是否使用 Claude CLI 执行任务
}

# 任务数据结构
{
  "id": "task-xxx",
  "title": "优化登录流程",
  "status": "pending | ... | pending_confirmation | completed",
  "subtasks": [...],    # 子任务列表
  "conversation": [...],# 对话历史
  "summary": "任务摘要"
}

# 老板要求数据结构
{
  "id": "dir-xxx",
  "content": "代码必须有完善的注释",
  "category": "general | quality | style | process | tech",
  "active": true,       # 是否生效
  "created_at": "...",
  "updated_at": "..."
}
```

### 数据存储

所有数据存储在项目根目录：
```
.oh_my_code/
└── workbench_state.json
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `/roles` | 查看组织架构 |
| `/tasks` | 查看任务列表 |
| `/use <角色名>` | 切换当前角色 |
| `/status` | 查看当前状态 |
| `/dashboard` | 打开 Dashboard API |
| `/c` | 清空对话 |
| `/debug` | 切换 Debug 模式 |
| `/stream` | 切换流式输出 |

## 前端开发

```bash
# 启动前端开发服务器
cd web
npm run dev

# 访问
http://localhost:3000
```

前端会自动代理 `/api` 请求到后端 `http://127.0.0.1:8765`。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/state` | 获取完整快照 |
| GET | `/api/roles` | 角色列表 |
| GET | `/api/roles/:id` | 单个角色 |
| POST | `/api/roles` | 新增员工 |
| PUT | `/api/roles/:id` | 更新角色 |
| DELETE | `/api/roles/:id` | 删除员工 |
| GET | `/api/tasks` | 任务列表 |
| POST | `/api/tasks` | 新增任务 |
| PUT | `/api/tasks/:id` | 更新任务 |
| POST | `/api/tasks/:id/subtasks` | 新增子任务 |
| GET | `/api/directives` | 老板要求列表 |
| POST | `/api/directives` | 新增老板要求 |
| PUT | `/api/directives/:id` | 更新老板要求 |
| DELETE | `/api/directives/:id` | 删除老板要求 |

## 配置说明

所有配置集中在 `lib/config.py`：

| 配置项 | 说明 |
|--------|------|
| `API_URL` | LLM API 地址 |
| `MODEL` | 默认模型名称 |
| `API_KEY` | 默认 API 密钥 |
| `MCP_SERVERS` | MCP Server 配置 |

**注意**：每个角色可以单独配置 API Key 和 Model，在 Web 前端中设置。

## 开发规范

- 纯 Python 标准库优先，避免不必要的第三方依赖
- 前端使用 React + TypeScript，保持零额外依赖（仅 Vite）
- 函数返回 `str` 类型结果，错误以 `"error: ..."` 前缀标识
