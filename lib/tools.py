"""内置工具实现与注册。"""

import glob as globlib
import html
import os
import re
import subprocess
import urllib.parse
import urllib.request

from .colors import DIM, RESET
from .config import BASH_TIMEOUT


# --------------- 工具实现 ---------------


def tool_read(args):
    """读取文件内容并附带行号。"""
    with open(args["path"], "r", encoding="utf-8") as f:
        lines = f.readlines()
    offset = args.get("offset", 0)
    limit = args.get("limit", len(lines))
    selected = lines[offset : offset + limit]
    return "".join(
        f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected)
    )


def tool_write(args):
    """写入文件。"""
    with open(args["path"], "w", encoding="utf-8") as f:
        f.write(args["content"])
    return "ok"


def tool_edit(args):
    """在文件中替换文本（old 必须唯一，除非 all=true）。"""
    with open(args["path"], "r", encoding="utf-8") as f:
        text = f.read()
    old, new = args["old"], args["new"]
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    if not args.get("all") and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = (
        text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
    )
    with open(args["path"], "w", encoding="utf-8") as f:
        f.write(replacement)
    return "ok"


def tool_glob(args):
    """按 glob 模式查找文件，按修改时间降序排列。"""
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


def tool_grep(args):
    """在文件中搜索正则表达式。"""
    pattern = re.compile(args["pat"])
    hits = []
    for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if pattern.search(line):
                        hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


def tool_bash(args):
    """执行 shell 命令并实时输出。"""
    proc = subprocess.Popen(
        args["cmd"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines = []
    try:
        if proc.stdout is not None:
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    print(f"    {DIM}┊ {line.rstrip()}{RESET}", flush=True)
                    output_lines.append(line)
        proc.wait(timeout=BASH_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append(f"\n(timed out after {BASH_TIMEOUT}s)")
    return "".join(output_lines).strip() or "(empty)"


def tool_search(args):
    """通过搜索引擎搜索信息并返回结果摘要。"""
    query = args["query"]
    engine = args.get("engine", "duckduckgo")  # 默认使用 DuckDuckGo（更友好）
    limit = args.get("limit", 5)  # 默认返回 5 个结果
    
    try:
        if engine.lower() == "duckduckgo":
            return _search_duckduckgo(query, limit)
       
        elif engine.lower() == "searx":
            return _search_searx(query, limit)
        else:
            return f"error: unsupported search engine '{engine}'. Use 'duckduckgo', 'bing', or 'searx'"
    except Exception as e:
        return f"error: search failed - {str(e)}"


def _search_duckduckgo(query, limit):
    """使用 DuckDuckGo 搜索（对自动化更友好）。"""
    import json
    import time
    import random
    
    # 添加随机延迟避免被检测
    time.sleep(random.uniform(0.5, 1.5))
    
    encoded_query = urllib.parse.quote_plus(query)
    
    # 使用 DuckDuckGo 的即时答案 API
    api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        results = []
        
        # 处理即时答案
        if data.get('Abstract'):
            results.append(f"• {data.get('Heading', 'Summary')}\n  {data.get('AbstractURL', '')}\n  {data['Abstract'][:300]}...\n")
        
        # 处理相关主题
        for topic in data.get('RelatedTopics', [])[:limit]:
            if isinstance(topic, dict) and 'Text' in topic:
                title = topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else topic.get('Text', '')[:100]
                url = topic.get('FirstURL', '')
                text = topic.get('Text', '')[:200]
                results.append(f"• {title}\n  {url}\n  {text}...\n")
        
        if not results:
            # 如果 API 没有结果，尝试搜索页面
            return _search_duckduckgo_html(query, limit)
        
        return f"Search Results (DuckDuckGo):\n\n" + "\n".join(results[:limit])
        
    except Exception as e:
        # API 失败时回退到 HTML 搜索
        return _search_duckduckgo_html(query, limit)


def _search_duckduckgo_html(query, limit):
    """DuckDuckGo HTML 搜索（备用方案）。"""
    import time
    import random
    
    time.sleep(random.uniform(1, 2))
    
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        html_content = response.read().decode('utf-8', errors='ignore')
    
    return _extract_duckduckgo_results(html_content, limit)


def _search_searx(query, limit):
    """使用 SearX 公共实例搜索。"""
    import json
    import time
    import random
    
    time.sleep(random.uniform(0.3, 1.0))
    
    # SearX 公共实例列表
    searx_instances = [
        "https://searx.be",
        "https://search.sapti.me",
        "https://searx.xyz",
        "https://searx.info",
    ]
    
    encoded_query = urllib.parse.quote_plus(query)
    
    for instance in searx_instances:
        try:
            api_url = f"{instance}/search?q={encoded_query}&format=json&categories=general"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            results = []
            for item in data.get('results', [])[:limit]:
                title = item.get('title', '')
                url = item.get('url', '')
                content = item.get('content', '')[:200]
                results.append(f"• {title}\n  {url}\n  {content}...\n")
            
            if results:
                return f"Search Results (SearX):\n\n" + "\n".join(results)
                
        except Exception:
            continue  # 尝试下一个实例
    
    return "error: all SearX instances failed"


def _extract_duckduckgo_results(html_content, limit):
    """从 DuckDuckGo HTML 中提取搜索结果。"""
    results = []
    
    # DuckDuckGo 结果提取模式
    pattern = r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    for url, title, snippet in matches[:limit]:
        title = html.unescape(title.strip())
        snippet = html.unescape(re.sub(r'<[^>]+>', '', snippet.strip()))
        results.append(f"• {title}\n  {url}\n  {snippet[:200]}...\n")
    
    if not results:
        # 尝试另一种模式
        pattern2 = r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>([^<]+)</a></h2>.*?<span[^>]*>([^<]+)</span>'
        matches2 = re.findall(pattern2, html_content, re.DOTALL | re.IGNORECASE)
        
        for url, title, snippet in matches2[:limit]:
            title = html.unescape(title.strip())
            snippet = html.unescape(re.sub(r'<[^>]+>', '', snippet.strip()))
            results.append(f"• {title}\n  {url}\n  {snippet[:200]}...\n")
    
    if not results:
        return "No search results found. The search may have been blocked or the page format changed."
    
    return f"Search Results (DuckDuckGo):\n\n" + "\n".join(results)


def tool_browse(args):
    """访问指定网页并提取文本内容。"""
    url = args["url"]
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
        
        # 提取标题
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
        title = html.unescape(title_match.group(1).strip()) if title_match else "No title"
        
        # 移除脚本和样式标签
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 提取文本内容
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        text_content = html.unescape(text_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # 限制长度
        max_length = 3000
        if len(text_content) > max_length:
            text_content = text_content[:max_length] + "...\n\n[Content truncated]"
        
        return f"Title: {title}\nURL: {url}\n\nContent:\n{text_content}"
        
    except Exception as e:
        return f"error: failed to browse {url} - {str(e)}"


# --------------- 工具注册表 ---------------

# 每个工具：(描述, 参数 schema 简写, 实现函数)
# 参数类型后缀 "?" 表示可选
TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        tool_read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        tool_write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        tool_edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        tool_glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        tool_grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        tool_bash,
    ),
    "search": (
        "Search the web using search engines (duckduckgo/searx)",
        {"query": "string", "engine": "string?", "limit": "number?"},
        tool_search,
    ),
    "browse": (
        "Browse a specific webpage and extract its text content",
        {"url": "string"},
        tool_browse,
    ),
}


def run_tool(name, args):
    """执行指定工具，捕获异常返回错误信息。"""
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def make_schema():
    """将工具注册表转换为 Anthropic API tools schema 格式。"""
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {
                "type": "integer" if base_type == "number" else base_type
            }
            if not is_optional:
                required.append(param_name)
        result.append(
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return result
