"""封装与 LLM API 的通信。"""

import json
import urllib.request

from .config import API_KEY, API_URL, API_VERSION, MAX_TOKENS, MODEL, OPENROUTER_KEY
from .tools import make_schema


def _build_headers(stream=False):
    auth = (
        {"Authorization": f"Bearer {OPENROUTER_KEY}"}
        if OPENROUTER_KEY
        else {"x-api-key": API_KEY}
    )
    h = {
        "Content-Type": "application/json",
        "anthropic-version": API_VERSION,
        **auth,
    }
    if stream:
        h["Accept"] = "text/event-stream"
    return h


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
        headers=_build_headers(),
    )
    response = urllib.request.urlopen(request)
    return json.loads(response.read())


def call_api_stream(messages, system_prompt):
    """
    流式请求，生成 (event_type, data)。
    event_type: "text_delta" | "content_blocks"
    - text_delta: data 为字符串，直接打印
    - content_blocks: data 为完整 content_blocks 列表，用于后续工具调用
    """
    req_body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
        "tools": make_schema(),
        "stream": True,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(req_body).encode(),
        headers=_build_headers(stream=True),
    )
    response = urllib.request.urlopen(request)

    content_blocks = []
    current_block = None
    current_index = -1
    input_json_buf = ""

    def _finalize_block():
        nonlocal current_block, input_json_buf
        if current_block is None:
            return
        if current_block.get("type") == "tool_use" and input_json_buf:
            try:
                current_block["input"] = json.loads(input_json_buf)
            except json.JSONDecodeError:
                current_block["input"] = {}
        content_blocks.append(current_block)
        current_block = None
        input_json_buf = ""

    buffer = ""
    event_type = None

    while True:
        chunk = response.read(4096).decode("utf-8", errors="replace")
        if not chunk:
            break
        buffer += chunk
        while "\n" in buffer or "\r" in buffer:
            line, _, buffer = buffer.partition("\n")
            line = line.rstrip("\r")
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:") and event_type:
                data_str = line[5:].strip()
                if data_str == "[DONE]" or data_str == "":
                    continue
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                ev = data.get("type", event_type)
                if ev == "message_start":
                    content_blocks.clear()
                elif ev == "content_block_start":
                    _finalize_block()
                    cb = data.get("content_block", {})
                    current_block = dict(cb)
                    current_index = data.get("index", 0)
                    if current_block.get("type") == "tool_use":
                        current_block["input"] = current_block.get("input") or {}
                        input_json_buf = ""
                    elif current_block.get("type") == "text":
                        current_block["text"] = current_block.get("text", "")
                elif ev == "content_block_delta":
                    delta = data.get("delta", {})
                    dt = delta.get("type")
                    idx = data.get("index", 0)
                    if dt == "text_delta" and idx == current_index and current_block:
                        text = delta.get("text", "")
                        if text:
                            current_block["text"] = current_block.get("text", "") + text
                            yield ("text_delta", text)
                    elif dt == "input_json_delta" and idx == current_index:
                        input_json_buf += delta.get("partial_json", "")
                elif ev == "content_block_stop":
                    _finalize_block()
                elif ev == "message_stop":
                    _finalize_block()
                    yield ("content_blocks", content_blocks)
                    return
                elif ev == "error":
                    err = data.get("error", {})
                    yield ("error", err.get("message", str(err)))
                    return
                event_type = None

    _finalize_block()
    if content_blocks:
        yield ("content_blocks", content_blocks)
