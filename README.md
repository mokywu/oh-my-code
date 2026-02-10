# oh-my-code

轻量级终端 AI 编程助手，零依赖（仅 Python 标准库），支持 Agentic 工具调用循环。

## 特性

- **零依赖** — 纯 Python 标准库，无需 `pip install`
- **Agentic Loop** — AI 自主调用工具，循环执行直到任务完成
- **流式输出** — LLM 响应逐字返回，减少等待感
- **9 个内置工具** — 读写文件、文本替换、文件搜索、正则搜索、Shell 命令、网页搜索、网页浏览、文件系统操作（list/copy/move/delete/mkdir 合并为 fs）
- **美化终端输出** — ANSI 彩色渲染，支持 Markdown 代码块、标题、列表等
- **多 API 支持** — 兼容 Anthropic / OpenRouter / Kimi 等 Claude Messages API 格式

## 快速开始

```bash
python index.py
```

### 交互命令

| 命令 | 说明 |
|------|------|
| `/q` 或 `exit` | 退出程序 |
| `/c` | 清空当前对话 |
| `/debug` | 切换 Debug 模式（显示工具返回的详细数据） |
| `/stream` | 切换流式输出（LLM 逐字返回） |
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

`STREAM_MODE = True` 可配置默认是否启用流式输出，运行时可用 `/stream` 切换。

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
| `fs` | 文件系统操作：action 为 list/copy/move/delete/mkdir（跨平台） |

## 项目结构

```
oh-my-code/
├── index.py            # 入口
└── lib/
    ├── config.py       # 配置（API 地址、密钥、模型）
    ├── colors.py       # ANSI 颜色常量 & 终端工具
    ├── tools.py        # 工具注册表 & 聚合入口
    ├── tool_file.py    # 文件读写、编辑、搜索（read/write/edit/glob/grep）
    ├── tool_shell.py   # Shell 命令（bash）
    ├── tool_web.py     # 网页搜索、浏览（search/browse）
    ├── tool_fs.py      # 文件系统操作（fs: list/copy/move/delete/mkdir）
    ├── api.py          # LLM API 通信
    ├── ui.py           # UI 渲染（Banner、分隔线、Markdown）
    └── agent.py        # Agent 主循环
```

## License

MIT
