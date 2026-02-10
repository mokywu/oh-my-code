"""应用配置：API 地址、模型、密钥等。"""

import os

# OpenRouter 密钥（为空则使用直连 API）
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- 默认 Anthropic 配置（已注释） ---
# API_URL = "https://openrouter.ai/api/v1/messages" if OPENROUTER_KEY else "https://api.anthropic.com/v1/messages"
# MODEL = os.environ.get("MODEL", "anthropic/claude-opus-4.5" if OPENROUTER_KEY else "claude-opus-4-5")
# ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- Kimi 配置 ---
API_URL = "https://api.kimi.com/coding/v1/messages"
MODEL = "kimi-for-coding"
API_KEY = "sk-kimi-54qkLwTfSMTkFFkb0RYsHbT7OAcm81thIzisz1QTyZ4n88KZMQN10hW85NSf91oh"

# API 请求参数
MAX_TOKENS = 8192
API_VERSION = "2023-06-01"

# 系统提示词模板
SYSTEM_PROMPT_TEMPLATE = "Concise coding assistant. cwd: {cwd}"

# 命令超时（秒）
BASH_TIMEOUT = 30

# Debug 模式（显示工具调用的详细数据）
DEBUG_MODE = False
