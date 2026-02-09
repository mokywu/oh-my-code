"""Agent 主循环：处理用户输入、调用 API、执行工具。"""

import os

from .api import call_api
from .colors import BLUE, BOLD, CYAN, DIM, GREEN, RED, RESET
from .config import SYSTEM_PROMPT_TEMPLATE
from .tools import run_tool
from .ui import print_banner, render_markdown, separator


def _handle_text_block(block):
    """渲染并打印文本块。"""
    rendered = render_markdown(block["text"])
    print(f"\n  {CYAN}●{RESET} {rendered}")


def _handle_tool_block(block):
    """执行工具调用并打印结果摘要，返回 tool_result dict。"""
    tool_name = block["name"]
    tool_args = block["input"]
    arg_preview = str(list(tool_args.values())[0])[:50]

    print(f"\n  {GREEN}⚙ {BOLD}{tool_name}{RESET} {DIM}→ {arg_preview}{RESET}")
    print(f"  {DIM}┊{RESET}")

    result = run_tool(tool_name, tool_args)
    result_lines = result.split("\n")
    preview = result_lines[0][:60]
    if len(result_lines) > 1:
        preview += f" {DIM}(+{len(result_lines) - 1} lines){RESET}"
    elif len(result_lines[0]) > 60:
        preview += "..."
    print(f"  {DIM}└─ ✓ {preview}{RESET}")

    return {
        "type": "tool_result",
        "tool_use_id": block["id"],
        "content": result,
    }


def _agent_loop(messages, system_prompt):
    """持续调用 API 直到没有工具调用为止。"""
    while True:
        response = call_api(messages, system_prompt)
        content_blocks = response.get("content", [])
        tool_results = []

        for block in content_blocks:
            if block["type"] == "text":
                _handle_text_block(block)
            if block["type"] == "tool_use":
                tool_results.append(_handle_tool_block(block))

        messages.append({"role": "assistant", "content": content_blocks})

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})


def run():
    """应用入口：打印 Banner，进入交互循环。"""
    print_banner()

    messages = []
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(cwd=os.getcwd())

    while True:
        try:
            print(separator("heavy"))
            user_input = input(f"  {BOLD}{BLUE}▶ {RESET}").strip()
            if not user_input:
                continue

            if user_input in ("/q", "exit"):
                print(f"\n  {DIM}👋 Bye!{RESET}\n")
                break

            if user_input == "/c":
                messages = []
                print(f"\n  {GREEN}✓ 对话已清空{RESET}\n")
                continue

            print(separator("dot"))
            messages.append({"role": "user", "content": user_input})
            _agent_loop(messages, system_prompt)
            print()

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {DIM}👋 Bye!{RESET}\n")
            break
        except Exception as err:
            print(f"\n  {RED}{BOLD}✖ Error:{RESET} {RED}{err}{RESET}\n")
