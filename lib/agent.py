"""Agent 主循环：处理用户输入、调用 API、执行工具。"""

import os

from .api import call_api, call_api_stream
from .colors import BLUE, BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from .config import STREAM_MODE, SYSTEM_PROMPT_TEMPLATE
from .tools import get_platform, run_tool
from .ui import print_banner, render_markdown, separator


def _handle_text_block(block):
    """渲染并打印文本块。"""
    rendered = render_markdown(block["text"])
    print(f"\n  {CYAN}●{RESET} {rendered}")


def _stream_text(text):
    """流式打印文本（逐字输出）。"""
    print(text, end="", flush=True)


def _handle_tool_block(block, debug_mode=False):
    """执行工具调用并打印结果摘要，返回 tool_result dict。"""
    tool_name = block["name"]
    tool_args = block["input"]
    arg_preview = str(list(tool_args.values())[0])[:50] if tool_args else "(no args)"

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


def _agent_loop_stream(messages, system_prompt, debug_mode):
    """流式调用 API，返回 content_blocks。"""
    first_chunk = True
    content_blocks = None
    try:
        stream_iter = call_api_stream(messages, system_prompt)
    except Exception as e:
        print(f"\n  {RED}流式请求失败，回退到普通模式: {e}{RESET}")
        return None  # 调用方将回退到非流式
    for event_type, data in stream_iter:
        if event_type == "text_delta":
            if first_chunk:
                print(f"\n  {CYAN}●{RESET} ", end="", flush=True)
                first_chunk = False
            _stream_text(data)
        elif event_type == "content_blocks":
            content_blocks = data
            if not first_chunk:
                print()  # 换行
        elif event_type == "error":
            print(f"\n  {RED}{BOLD}✖ API Error:{RESET} {RED}{data}{RESET}")
            return []
    return content_blocks or []


def _agent_loop(messages, system_prompt, debug_mode=False, stream=True):
    """持续调用 API 直到没有工具调用为止。"""
    while True:
        if stream:
            content_blocks = _agent_loop_stream(messages, system_prompt, debug_mode)
            if content_blocks is None:
                # 流式失败，回退到普通请求
                response = call_api(messages, system_prompt)
                content_blocks = response.get("content", [])
                for block in content_blocks:
                    if block["type"] == "text":
                        _handle_text_block(block)
        else:
            response = call_api(messages, system_prompt)
            content_blocks = response.get("content", [])
            for block in content_blocks:
                if block["type"] == "text":
                    _handle_text_block(block)

        tool_results = []
        for block in content_blocks:
            if block.get("type") == "tool_use":
                tool_results.append(_handle_tool_block(block, debug_mode))

        messages.append({"role": "assistant", "content": content_blocks})

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})


def run():
    """应用入口：打印 Banner，进入交互循环。"""
    print_banner()
    
    # 初始化 MCP
    try:
        from .mcp_client import init_mcp
        init_mcp()
    except:
        pass

    messages = []
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(cwd=os.getcwd(), platform=get_platform())
    debug_mode = False
    stream_mode = [STREAM_MODE]  # 可变的，供 /stream 切换

    while True:
        try:
            print(separator("heavy"))
            user_input = input(f"  {BOLD}{BLUE}▶ {RESET}").strip()
            if not user_input:
                continue

            if user_input in ("/q", "exit"):
                print(f"\n  {DIM}👋 Bye!{RESET}\n")
                # 清理 MCP
                try:
                    from .mcp_client import get_mcp_manager
                    get_mcp_manager().shutdown()
                except:
                    pass
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

            if user_input == "/stream":
                stream_mode[0] = not stream_mode[0]
                status = f"{GREEN}开启{RESET}" if stream_mode[0] else f"{DIM}关闭{RESET}"
                print(f"\n  {CYAN}📡 流式输出已{status}{RESET}\n")
                continue

            if user_input == "/help":
                print(f"\n  {CYAN}可用命令:{RESET}")
                print(f"  {DIM}/q, exit{RESET}  - 退出程序")
                print(f"  {DIM}/c{RESET}        - 清空对话")
                print(f"  {DIM}/debug{RESET}    - 切换 Debug 模式（显示工具返回的详细数据）")
                print(f"  {DIM}/stream{RESET}   - 切换流式输出")
                print(f"  {DIM}/help{RESET}     - 显示此帮助信息")
                print()
                continue

            print(separator("dot"))
            messages.append({"role": "user", "content": user_input})
            _agent_loop(messages, system_prompt, debug_mode, stream_mode[0])
            print()

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {DIM}👋 Bye!{RESET}\n")
            break
        except Exception as err:
            print(f"\n  {RED}{BOLD}✖ Error:{RESET} {RED}{err}{RESET}\n")
