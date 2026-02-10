"""文件读写、编辑、搜索工具。"""

import glob as globlib
import os
import re


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
