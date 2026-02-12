# oh-my-code

轻量级终端 AI 编程助手，支持 Agentic 工具调用循环 + MCP 工具扩展。

## 特性

- **Agentic Loop** — AI 自主调用工具，循环执行直到任务完成
- **流式输出** — LLM 响应逐字返回，减少等待感
- **10+ 内置工具** — 读写文件、文本替换、文件搜索、正则搜索、Shell 命令、网页搜索、网页浏览、文件系统操作
- **MCP 工具扩展** — 通过 MCP 协议接入外部工具服务器，无限扩展能力
- **美化终端输出** — ANSI 彩色渲染，支持 Markdown 代码块、标题、列表等
- **多 API 支持** — 兼容 Anthropic / OpenRouter / Kimi 等 Claude Messages API 格式

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18（MCP Server 需要）

### 安装

```bash
# 克隆项目
git clone <repo-url> && cd oh-my-code

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装依赖（开发模式）
pip install -e .
```

### 运行

```bash
# 方式一：通过入口脚本
python index.py

# 方式二：通过包命令（pip install -e . 后可用）
oh-my-code
```

### 交互命令

| 命令 | 说明 |
|------|------|
| `/q` 或 `exit` | 退出程序 |
| `/c` | 清空当前对话 |
| `/debug` | 切换 Debug 模式（显示工具返回的详细数据） |
| `/stream` | 切换流式输出（LLM 逐字返回） |
| `/mcp` | 查看 MCP 工具列表 |
| `/help` | 显示帮助信息 |

## 配置

编辑 `lib/config.py` 切换 API 提供商：

```python
# Anthropic 直连
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-opus-4-5"
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Kimi
API_URL = "https://api.kimi.com/coding/v1/messages"
MODEL = "kimi-for-coding"
API_KEY = "your-kimi-key"
```

### MCP 配置

在 `lib/config.py` 的 `MCP_SERVERS` 中添加 MCP Server：

```python
MCP_SERVERS = {
    "my-mcp": {
        "command": "node",
        "args": ["path/to/mcp-server/dist/index.js"],
        "env": {}  # 可选：环境变量
    }
}
```

启动后通过 `/mcp` 命令查看已加载的工具。

## 内置工具

| 工具 | 说明 |
|------|------|
| `read` | 读取文件内容（带行号） |
| `write` | 写入文件 |
| `edit` | 文本替换（支持唯一性校验） |
| `glob` | 按模式查找文件，按修改时间排序 |
| `grep` | 正则搜索文件内容 |
| `bash` | 执行 Shell 命令（30s 超时） |
| `search` | 网页搜索（支持 DuckDuckGo/SearX） |
| `browse` | 访问指定网页并提取文本内容 |
| `fs` | 文件系统操作：list/copy/move/delete/mkdir（跨平台） |
| `mcp` | MCP 工具管理 |

## 项目结构

```
oh-my-code/
├── index.py            # 入口
├── pyproject.toml      # 项目元数据 & 依赖管理
└── lib/
    ├── config.py       # 配置（API 地址、密钥、模型、MCP）
    ├── colors.py       # ANSI 颜色常量
    ├── tools.py        # 工具注册表 & 聚合入口
    ├── tool_file.py    # 文件读写、编辑、搜索
    ├── tool_shell.py   # Shell 命令
    ├── tool_web.py     # 网页搜索、浏览
    ├── tool_fs.py      # 文件系统操作
    ├── tool_mcp.py     # MCP 工具桥接
    ├── mcp_client.py   # MCP 客户端（基于官方 SDK）
    ├── api.py          # LLM API 通信
    ├── ui.py           # UI 渲染
    └── agent.py        # Agent 主循环
```

## License

MIT
