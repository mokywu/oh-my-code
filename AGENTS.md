# AGENTS.md - 本地开发指南

## 环境搭建

### 前置条件

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.10 | 运行主程序 |
| pip | 最新 | 包管理 |
| Node.js | >= 18 | MCP Server 运行时 |

### 初始化步骤

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2. 安装项目（开发模式，可编辑代码即时生效）
pip install -e .

# 3. 验证安装
python index.py
# 或
oh-my-code
```

### 依赖管理

项目使用 `pyproject.toml` 管理依赖（PEP 621 标准）。

```bash
# 添加新依赖：编辑 pyproject.toml 的 [project].dependencies，然后
pip install -e .

# 查看当前已安装的包
pip list
```

当前唯一的第三方依赖是 `mcp`（官方 MCP Python SDK），其余全部使用 Python 标准库。

## 项目架构

```
index.py  →  lib/agent.py (主循环)
                ├── lib/api.py       (LLM API 通信)
                ├── lib/tools.py     (工具注册 & 分发)
                │     ├── tool_file.py
                │     ├── tool_shell.py
                │     ├── tool_web.py
                │     ├── tool_fs.py
                │     └── tool_mcp.py → mcp_client.py (MCP SDK)
                ├── lib/ui.py        (终端渲染)
                ├── lib/colors.py    (ANSI 颜色)
                └── lib/config.py    (配置)
```

### 核心流程

1. `agent.py:run()` 启动 → 初始化 MCP → 进入交互循环
2. 用户输入 → 构造 messages → 调用 LLM API
3. LLM 返回 tool_use → `tools.py:run_tool()` 分发执行
4. 工具结果 → 追加到 messages → 再次调用 LLM（循环直到无 tool_use）

### MCP 工具调用链路

```
LLM 返回 tool_use (name="mcp__server__tool")
  → tools.py:run_tool() 识别 "mcp__" 前缀
  → mcp_client.py:MCPManager.resolve_tool() 解析 server + tool
  → MCPManager.call() → MCPClient.call_tool() (异步)
  → 官方 MCP SDK stdio_client 通信
  → MCP Server 执行并返回结果
```

## 开发规范

### 添加新内置工具

1. 在 `lib/` 下创建 `tool_xxx.py`，实现 `tool_xxx(args: dict) -> str`
2. 在 `lib/tools.py` 的 `TOOLS` 字典中注册
3. 参数类型后缀 `?` 表示可选（如 `"path": "string?"`）

### 添加新 MCP Server

在 `lib/config.py` 的 `MCP_SERVERS` 中添加配置：

```python
MCP_SERVERS = {
    "server-name": {
        "command": "node",           # 可执行文件
        "args": ["path/to/index.js"], # 参数
        "env": {}                     # 可选环境变量
    }
}
```

MCP 工具会自动注册，对外暴露为 `mcp__<server>__<tool>` 格式。

### 配置说明

所有配置集中在 `lib/config.py`：

| 配置项 | 说明 |
|--------|------|
| `API_URL` | LLM API 地址 |
| `MODEL` | 模型名称 |
| `API_KEY` | API 密钥 |
| `MAX_TOKENS` | 最大返回 token |
| `STREAM_MODE` | 默认是否流式输出 |
| `DEBUG_MODE` | 默认是否 Debug 模式 |
| `BASH_TIMEOUT` | Shell 命令超时秒数 |
| `MCP_SERVERS` | MCP Server 配置 |

### 代码风格

- 纯 Python 标准库优先，避免不必要的第三方依赖
- 每个工具模块独立，通过 `tools.py` 统一注册
- 函数返回 `str` 类型结果，错误以 `"error: ..."` 前缀标识
