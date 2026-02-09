"""终端 UI 渲染：Banner、分隔线、Markdown 渲染。"""

import os
import re

from .colors import (
    BG_GRAY, BOLD, CYAN, DIM, GREEN, ITALIC, MAGENTA, RESET, WHITE, YELLOW,
    get_width,
)
from .config import MODEL, OPENROUTER_KEY


# --------------- 分隔线 ---------------

_SEPARATOR_STYLES = {
    "heavy":  lambda w: f"{DIM}{CYAN}{'━' * w}{RESET}",
    "double": lambda w: f"{DIM}{'═' * w}{RESET}",
    "dot":    lambda w: f"{DIM}{'┄' * w}{RESET}",
    "light":  lambda w: f"{DIM}{'─' * w}{RESET}",
}


def separator(style="light"):
    """返回指定风格的分隔线字符串。"""
    renderer = _SEPARATOR_STYLES.get(style, _SEPARATOR_STYLES["light"])
    return renderer(get_width())


# --------------- Markdown 渲染 ---------------


def render_markdown(text):
    """增强 Markdown 渲染：代码块、标题、列表、行内格式。"""
    lines = text.split("\n")
    result = []
    in_code_block = False
    w = get_width()

    for line in lines:
        # 代码块 开始/结束
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                lang = line.strip()[3:].strip()
                lang_label = f" {DIM}{lang}{RESET}" if lang else ""
                result.append(f"  {DIM}┌{'─' * (w - 4)}┐{RESET}{lang_label}")
            else:
                in_code_block = False
                result.append(f"  {DIM}└{'─' * (w - 4)}┘{RESET}")
            continue

        if in_code_block:
            result.append(f"  {DIM}│{RESET} {GREEN}{line}{RESET}")
            continue

        # 标题（### > ## > #）
        if line.startswith("### "):
            result.append(f"  {BOLD}{YELLOW}   {line[4:]}{RESET}")
            continue
        if line.startswith("## "):
            result.append(f"  {BOLD}{CYAN}  {line[3:]}{RESET}")
            continue
        if line.startswith("# "):
            result.append(f"  {BOLD}{MAGENTA}━ {line[2:]}{RESET}")
            continue

        # 列表项
        if re.match(r"^\s*[-*]\s", line):
            line = re.sub(r"^(\s*)[-*]\s", r"\1  ● ", line)
        elif re.match(r"^\s*\d+\.\s", line):
            line = re.sub(r"^(\s*)(\d+)\.\s", r"\1  \2. ", line)

        # 行内格式
        line = re.sub(r"`([^`]+)`", f"{BG_GRAY}{WHITE} \\1 {RESET}", line)
        line = re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", line)
        line = re.sub(r"\*(.+?)\*", f"{ITALIC}\\1{RESET}", line)

        result.append(line)

    return "\n".join(result)


# --------------- 启动 Banner ---------------


def _center_in_box(text, width):
    """在指定宽度内居中文本，返回 (左填充, 右填充)。"""
    pad = width - len(text)
    left = pad // 2
    return left, pad - left


def print_banner():
    """打印启动 Banner。"""
    w = get_width()
    inner = w - 4  # 去掉左右边框和缩进

    print()
    print(f"{BOLD}{CYAN}  ╔{'═' * inner}╗{RESET}")
    print(f"{BOLD}{CYAN}  ║{RESET}{' ' * inner}{BOLD}{CYAN}║{RESET}")

    title = "⚡ oh-my-code"
    lp, rp = _center_in_box(title, inner)
    print(f"{BOLD}{CYAN}  ║{RESET}{' ' * lp}{BOLD}{WHITE}{title}{RESET}{' ' * rp}{BOLD}{CYAN}║{RESET}")

    subtitle = f"{MODEL} | {'OpenRouter' if OPENROUTER_KEY else 'Direct API'}"
    lp2, rp2 = _center_in_box(subtitle, inner)
    print(f"{BOLD}{CYAN}  ║{RESET}{' ' * lp2}{DIM}{subtitle}{RESET}{' ' * rp2}{BOLD}{CYAN}║{RESET}")

    print(f"{BOLD}{CYAN}  ║{RESET}{' ' * inner}{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}  ╚{'═' * inner}╝{RESET}")
    print()
    print(f"  {DIM}📂 {os.getcwd()}{RESET}")
    print(f"  {DIM}💡 输入 /q 退出  /c 清空对话{RESET}")
    print()
