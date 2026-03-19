"""封装与 LLM API 的通信。"""

import json
import http.client
import urllib.request
import urllib.error


from .config import API_KEY, API_URL, API_VERSION, MAX_TOKENS, MODEL, OPENROUTER_KEY
from .tools import make_schema


def _read_response_bytes(response):
    """读取响应字节，容忍服务端提前断开连接。"""
    try:
        return response.read()
    except http.client.IncompleteRead as e:
        return e.partial


def _read_stream_chunk(response, chunk_size):
    """读取流式响应块，容忍服务端提前断开连接。"""
    try:
        return response.read(chunk_size), False
    except http.client.IncompleteRead as e:
        return e.partial, True


def _build_headers(api_key=None, stream=False):

    """构建请求头，支持自定义 API Key。"""
    key = api_key or API_KEY
    use_openrouter = OPENROUTER_KEY and not api_key  # 使用自定义 key 时不走 openrouter
    
    auth = (
        {"Authorization": f"Bearer {OPENROUTER_KEY}"}
        if use_openrouter
        else {"x-api-key": key}
    )
    h = {
        "Content-Type": "application/json",
        "anthropic-version": API_VERSION,
        **auth,
    }
    if stream:
        h["Accept"] = "text/event-stream"
    return h


def call_api(messages, system_prompt, api_key=None, model=None, api_url=None, max_tokens=None, for_cto=False):
    """发送消息到 LLM API 并返回解析后的 JSON 响应。
    
    Args:
        messages: 消息列表
        system_prompt: 系统提示
        api_key: 可选的自定义 API Key
        model: 可选的自定义模型
        api_url: 可选的自定义 API 地址
        max_tokens: 可选的最大 token 数
        for_cto: 是否为 CTO 调用（使用受限工具列表）
    """
    from .config import MAX_TOKENS as DEFAULT_MAX_TOKENS
    
    url = api_url or API_URL
    use_model = model or MODEL
    use_max_tokens = max_tokens or DEFAULT_MAX_TOKENS
    
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "model": use_model,
                "max_tokens": use_max_tokens,
                "system": system_prompt,
                "messages": messages,
                "tools": make_schema(for_cto=for_cto),
            }
        ).encode(),
        headers=_build_headers(api_key=api_key),
    )
    try:
        response = urllib.request.urlopen(request)
        body = _read_response_bytes(response)
        return json.loads(body.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"\n✖ API Error {e.code}: {e.reason}")
        print(f"  Response: {error_body}")
        raise
    except json.JSONDecodeError as e:
        raise RuntimeError(f"API 响应不是有效 JSON: {e}") from e



def call_api_stream(messages, system_prompt, for_cto=False):
    """
    流式请求，生成 (event_type, data)。
    event_type: "text_delta" | "content_blocks"
    - text_delta: data 为字符串，直接打印
    - content_blocks: data 为完整 content_blocks 列表，用于后续工具调用
    
    Args:
        messages: 消息列表
        system_prompt: 系统提示
        for_cto: 是否为 CTO 调用（使用受限工具列表）
    """
    req_body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
        "tools": make_schema(for_cto=for_cto),
        "stream": True,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(req_body).encode(),
        headers=_build_headers(stream=True),
    )
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"\n✖ API Error {e.code}: {e.reason}")
        print(f"  Response: {error_body}")
        raise

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
        chunk_bytes, reached_end = _read_stream_chunk(response, 4096)


        if not chunk_bytes:
            break

        chunk = chunk_bytes.decode("utf-8", errors="replace")
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

        if reached_end:
            break


    _finalize_block()
    if content_blocks:
        yield ("content_blocks", content_blocks)
