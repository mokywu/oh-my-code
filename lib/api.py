"""封装与 LLM API 的通信。"""

import json
import urllib.request

from .config import API_KEY, API_URL, API_VERSION, MAX_TOKENS, MODEL, OPENROUTER_KEY
from .tools import make_schema


def call_api(messages, system_prompt):
    """发送消息到 LLM API 并返回解析后的 JSON 响应。"""
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": system_prompt,
                "messages": messages,
                "tools": make_schema(),
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "anthropic-version": API_VERSION,
            **(
                {"Authorization": f"Bearer {OPENROUTER_KEY}"}
                if OPENROUTER_KEY
                else {"x-api-key": API_KEY}
            ),
        },
    )
    response = urllib.request.urlopen(request)
    return json.loads(response.read())
