"""应用配置：API 地址、模型、密钥等。"""

import os

# OpenRouter 密钥（为空则使用直连 API）
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- 默认 Anthropic 配置（已注释） ---
# API_URL = "https://openrouter.ai/api/v1/messages" if OPENROUTER_KEY else "https://api.anthropic.com/v1/messages"
# MODEL = os.environ.get("MODEL", "anthropic/claude-opus-4.5" if OPENROUTER_KEY else "claude-opus-4-5")
# ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- Kimi 配置 ---
# API_URL = "https://api.kimi.com/coding/v1/messages"
# MODEL = "kimi-for-coding"
# API_KEY = "sk-kimi-54qkLwTfSMTkFFkb0RYsHbT7OAcm81thIzisz1QTyZ4n88KZMQN10hW85NSf91oh"

API_URL = "http://10.3.0.9:9092/v1/messages"
MODEL = "azure/gpt-4.1"
API_KEY = "1234567890"

# ---大师的 配置 ---
# API_URL = "https://api.minimaxi.com/anthropic/v1/messages"
# MODEL = "MiniMax-M2.5"
# API_KEY = "sk-cp-1uTZl9wymUUSRUBubH4MlbN7mn4LwuJuDm71VElpv0eUM-r7a8QLINSav-P-zQZUg7VhU-wI8cppc_VZ7fxvGTBZZkg-WMLUvc5P8U-LaTSU-Kp7hL9AnrM"


# API 请求参数
MAX_TOKENS = 8192
API_VERSION = "2023-06-01"

# 系统提示词模板
SYSTEM_PROMPT_TEMPLATE = "Concise coding assistant. cwd: {cwd}, platform: {platform}"

# 命令超时（秒）
BASH_TIMEOUT = 30

# Debug 模式（显示工具调用的详细数据）
DEBUG_MODE = False

# 流式输出（LLM 逐字返回）
STREAM_MODE = True

# 员工 Claude CLI 模式是否跳过权限确认
# true = 直接跳过（无需 Web 审批，自动带 --dangerously-skip-permissions）
# false = 需要老板在 Web Dashboard 审批后才执行（推荐）
CLAUDE_SKIP_PERMISSIONS = os.environ.get("CLAUDE_SKIP_PERMISSIONS", "false").lower() == "true"

# 工具注册表
MCP_SERVERS = {
    "chrome-devtools-mcp": {
      "args": [
        "--port",
        "8081"
      ],
      "command": "chrome-devtools-mcp"
    }
}