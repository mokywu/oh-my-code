# oh-my-code

轻量级终端 AI 编程助手，零依赖（仅 Python 标准库），支持 Agentic 工具调用循环。

## 特性

- **零依赖** — 纯 Python 标准库，无需 `pip install`
- **Agentic Loop** — AI 自主调用工具，循环执行直到任务完成
- **6 个内置工具** — 读写文件、文本替换、文件搜索、正则搜索、Shell 命令
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

## 内置工具

| 工具 | 说明 |
|------|------|
| `read` | 读取文件内容（带行号） |
| `write` | 写入文件 |
| `edit` | 文本替换（支持唯一性校验） |
| `glob` | 按模式查找文件，按修改时间排序 |
| `grep` | 正则搜索文件内容 |
| `bash` | 执行 Shell 命令（30s 超时） |

## 项目结构

```
oh-my-code/
├── index.py            # 入口
└── lib/
    ├── config.py       # 配置（API 地址、密钥、模型）
    ├── colors.py       # ANSI 颜色常量 & 终端工具
    ├── tools.py        # 工具实现 & 注册表 & Schema 生成
    ├── api.py          # LLM API 通信
    ├── ui.py           # UI 渲染（Banner、分隔线、Markdown）
    └── agent.py        # Agent 主循环
```

## License

MIT
