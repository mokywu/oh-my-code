"""Agent 主循环：处理用户输入、调用 API、执行工具。"""

import os

from .api import call_api
from .colors import BLUE, BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from .config import SYSTEM_PROMPT_TEMPLATE
from .tools import run_tool
from .ui import print_banner, render_markdown, separator


def _handle_text_block(block):
    """渲染并打印文本块。"""
    rendered = render_markdown(block["text"])
    print(f"\n  {CYAN}●{RESET} {rendered}")


def _handle_tool_block(block, debug_mode=False):
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

    # Debug 模式：显示完整的工具返回数据
    if debug_mode:
        print(f"\n  {YELLOW}🐛 DEBUG - Tool Result:{RESET}")
        print(f"  {DIM}┌{'─' * 60}┐{RESET}")
        for i, line in enumerate(result_lines[:20]):  # 最多显示前20行
            print(f"  {DIM}│{RESET} {line[:58]}")
        if len(result_lines) > 20:
            print(f"  {DIM}│{RESET} {DIM}... ({len(result_lines) - 20} more lines){RESET}")
        print(f"  {DIM}└{'─' * 60}┘{RESET}")

    return {
        "type": "tool_result",
        "tool_use_id": block["id"],
        "content": result,
    }


def _agent_loop(messages, system_prompt, debug_mode=False):
    """持续调用 API 直到没有工具调用为止。"""
    while True:
        response = call_api(messages, system_prompt)
        content_blocks = response.get("content", [])
        tool_results = []

        for block in content_blocks:
            if block["type"] == "text":
                _handle_text_block(block)
            if block["type"] == "tool_use":
                tool_results.append(_handle_tool_block(block, debug_mode))

        messages.append({"role": "assistant", "content": content_blocks})

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})


def run():
    """应用入口：打印 Banner，进入交互循环。"""
    print_banner()

    messages = []
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(cwd=os.getcwd())
    debug_mode = False  # 初始化 debug 模式为关闭

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

            if user_input == "/debug":
                debug_mode = not debug_mode
                status = f"{GREEN}开启{RESET}" if debug_mode else f"{DIM}关闭{RESET}"
                print(f"\n  {YELLOW}🐛 Debug 模式已{status}{RESET}\n")
                continue

            if user_input == "/help":
                print(f"\n  {CYAN}可用命令:{RESET}")
                print(f"  {DIM}/q, exit{RESET}  - 退出程序")
                print(f"  {DIM}/c{RESET}        - 清空对话")
                print(f"  {DIM}/debug{RESET}    - 切换 Debug 模式（显示工具返回的详细数据）")
                print(f"  {DIM}/help{RESET}     - 显示此帮助信息")
                print()
                continue

            print(separator("dot"))
            messages.append({"role": "user", "content": user_input})
            _agent_loop(messages, system_prompt, debug_mode)
            print()

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {DIM}👋 Bye!{RESET}\n")
            break
        except Exception as err:
            print(f"\n  {RED}{BOLD}✖ Error:{RESET} {RED}{err}{RESET}\n")
