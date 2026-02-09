"""内置工具实现与注册。"""

import glob as globlib
import os
import re
import subprocess

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
