"""网页搜索与浏览工具。"""

import html
import json
import re
import time
import random
import urllib.parse
import urllib.request


def tool_search(args):
    """通过搜索引擎搜索信息并返回结果摘要。"""
    query = args["query"]
    engine = args.get("engine", "duckduckgo")
    limit = args.get("limit", 5)
    try:
        if engine.lower() == "duckduckgo":
            return _search_duckduckgo(query, limit)
        elif engine.lower() == "searx":
            return _search_searx(query, limit)
        else:
            return f"error: unsupported search engine '{engine}'. Use 'duckduckgo' or 'searx'"
    except Exception as e:
        return f"error: search failed - {str(e)}"


def _search_duckduckgo(query, limit):
    time.sleep(random.uniform(0.5, 1.5))
    encoded_query = urllib.parse.quote_plus(query)
    api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        results = []
        if data.get("Abstract"):
            results.append(f"• {data.get('Heading', 'Summary')}\n  {data['Abstract'][:300]}...\n")
        for topic in data.get("RelatedTopics", [])[:limit]:
            if isinstance(topic, dict) and "Text" in topic:
                text = topic.get("Text", "")[:200]
                url = topic.get("FirstURL", "")
                results.append(f"• {text}\n  {url}\n")
        if not results:
            return _search_duckduckgo_html(query, limit)
        return f"Search Results (DuckDuckGo):\n\n" + "\n".join(results[:limit])
    except Exception:
        return _search_duckduckgo_html(query, limit)


def _search_duckduckgo_html(query, limit):
    time.sleep(random.uniform(1, 2))
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/html/?q={encoded_query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        html_content = response.read().decode("utf-8", errors="ignore")
    return _extract_duckduckgo_results(html_content, limit)


def _search_searx(query, limit):
    time.sleep(random.uniform(0.3, 1.0))
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
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            results = []
            for item in data.get("results", [])[:limit]:
                title = item.get("title", "")
                url = item.get("url", "")
                content = item.get("content", "")[:200]
                results.append(f"• {title}\n  {url}\n  {content}...\n")
            if results:
                return f"Search Results (SearX):\n\n" + "\n".join(results)
        except Exception:
            continue
    return "error: all SearX instances failed"


def _extract_duckduckgo_results(html_content, limit):
    results = []
    pattern = r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
    for url, title, snippet in matches[:limit]:
        title = html.unescape(title.strip())
        snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet.strip()))
        results.append(f"• {title}\n  {url}\n  {snippet[:200]}...\n")
    if not results:
        pattern2 = r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>([^<]+)</a></h2>.*?<span[^>]*>([^<]+)</span>'
        matches2 = re.findall(pattern2, html_content, re.DOTALL | re.IGNORECASE)
        for url, title, snippet in matches2[:limit]:
            title = html.unescape(title.strip())
            snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet.strip()))
            results.append(f"• {title}\n  {url}\n  {snippet[:200]}...\n")
    if not results:
        return "No search results found."
    return f"Search Results (DuckDuckGo):\n\n" + "\n".join(results)


def tool_browse(args):
    """访问指定网页并提取文本内容。"""
    url = args["url"]
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode("utf-8", errors="ignore")
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
        title = html.unescape(title_match.group(1).strip()) if title_match else "No title"
        html_content = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r"<[^>]+>", " ", html_content)
        text_content = html.unescape(text_content)
        text_content = re.sub(r"\s+", " ", text_content).strip()
        if len(text_content) > 3000:
            text_content = text_content[:3000] + "...\n\n[Content truncated]"
        return f"Title: {title}\nURL: {url}\n\nContent:\n{text_content}"
    except Exception as e:
        return f"error: failed to browse {url} - {str(e)}"
