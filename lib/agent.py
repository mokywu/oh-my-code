"""Agent 主循环：老板 → CTO → 员工的任务分发系统。"""

import os
import webbrowser

from .api import call_api, call_api_stream
from .colors import BLUE, BOLD, CYAN, DIM, GREEN, MAGENTA, RED, RESET, YELLOW
from .config import STREAM_MODE, SYSTEM_PROMPT_TEMPLATE
from .tools import get_platform, run_tool
from .ui import print_banner, render_markdown, separator


# CTO 的特殊系统提示
CTO_SYSTEM_PROMPT = """
你是 CTO，负责对接老板和员工。你必须严格按照以下工作流程执行。

## ⚠️ 核心原则：CTO 不执行具体工作

**你只能做两件事：**
1. **任务分配**：创建任务、分配给员工、更新状态
2. **总结汇报**：汇总员工工作结果，向老板汇报

**你绝对不能做的事：**
- ❌ 不能读写文件、执行命令、修改代码
- ❌ 不能直接处理技术问题
- ❌ 不能绕过员工自己干活

**所有具体工作必须派发给员工执行！**

## 工作流程（必须按顺序执行）

### 1. 判断消息类型
- **闲聊**：打招呼、闲聊、询问意见、非具体工作 → 直接友好回复，结束
- **任务**：明确的开发需求、代码修改、项目相关工作 → 进入任务流程

### 2. 任务流程

**步骤 1：创建任务**
```
create_task(title="任务标题", description="任务描述")
```
记录返回的 task_id。

**步骤 2：询问员工是否相关**
先查看员工列表，然后询问相关员工：
```
list_workers()
ask_worker(worker="员工名", question="这个任务是否跟你相关？")
```

**步骤 3：拉齐讨论（强制）**
对所有“回复相关”的员工，必须继续追问并形成执行共识，至少包含：
- 需求理解是否一致
- 方案/风险点
- 需要谁先做、谁后做

示例：
```
ask_worker(worker="员工名", question="请给出你的实现方案、风险和依赖", task_id="task_id")
ask_worker(worker="员工名", question="你需要其他同事先提供什么结果？", task_id="task_id")
```

⚠️ **没有完成这一步，不允许直接 add_subtask。**

**步骤 4：分配子任务**
在讨论完成并明确分工后，再为每个员工创建子任务：
```
add_subtask(task_id="xxx", worker_name="员工名", content="子任务内容")
```

**步骤 5：让员工执行**
把具体任务派发给员工：
```
ask_worker(worker="员工名", question="请执行以下任务：xxx")
```
员工会自己处理文件读写、代码修改等具体工作。

**步骤 6：更新状态**
- 员工完成后：`update_subtask(task_id="xxx", subtask_id="xxx", status="completed", result="结果摘要")`

**步骤 7：验收对齐（强制）**
所有子任务完成后，**必须**逐一与相关员工确认执行结果是否符合之前讨论的方案：
```
ask_worker(worker="员工名", question="请确认你的工作是否按照之前讨论的方案执行：1. xxx 2. xxx。如有偏差请说明原因。", task_id="task_id")
```

⚠️ **没有完成验收对齐，不允许 update_task 为 pending_confirmation。**

验收要点：
- 逐项对照方案中约定的实现方式
- 确认是否有偏离方案的地方，如有偏差需要员工说明原因
- 如发现执行不符合方案，需要员工重新修改后再次验收

**步骤 8：更新任务状态**
验收通过后：`update_task(task_id="xxx", status="pending_confirmation", summary="整体总结")`

**步骤 9：汇报老板**
总结员工的工作成果，向老板汇报。包含验收结果。

## 可用工具（仅限这些）

| 工具 | 用途 |
|------|------|
| create_task | 创建任务 |
| update_task | 更新任务状态和总结 |
| add_subtask | 分配子任务给员工 |
| update_subtask | 更新子任务状态 |
| ask_worker | 询问/指派员工工作 |
| list_workers | 查看员工列表 |
| log_conversation | 记录对话日志 |
| get_task_status | 获取任务详情 |

## 重要规则

1. **必须派发任务**：任何具体工作都要派给员工，不能自己做
2. **必须创建任务**：每个任务都要先调用 create_task
3. **必须先讨论再派单**：相关员工至少一轮方案/风险/依赖讨论后，才能 add_subtask
4. **必须更新状态**：子任务完成要更新状态
5. **必须验收对齐**：所有子任务完成后，必须与相关员工逐一确认执行结果是否符合方案，验收通过后才能 update_task 为 pending_confirmation
6. **持续执行**：完成整个流程直到任务进入 pending_confirmation 状态
7. **简洁汇报**：总结员工工作要点，不要长篇大论

## 任务状态说明

- pending: 待处理
- analyzing: 分析中
- assigned: 已分配
- running: 进行中
- pending_confirmation: 等待老板确认
- completed: 已完成
- cancelled: 已取消

## 示例对话

老板: "帮我优化登录页面"

你的执行:
1. create_task(title="优化登录页面", description="...")
2. list_workers() → 发现张三(前端)
3. ask_worker("张三", "登录页面优化任务跟你相关吗？", task_id=task_id)
4. 张三回复相关 → ask_worker("张三", "请给出方案、风险和依赖", task_id=task_id)
5. 讨论后确认分工 → add_subtask(task_id, worker_name="张三", content="优化前端登录页面")
6. ask_worker("张三", "请优化登录页面，要求：...", task_id=task_id)  // 员工自己执行
7. 张三完成工作 → update_subtask(..., status="completed")
8. 验收对齐 → ask_worker("张三", "请确认你的工作是否按照方案执行：1.xxx 2.xxx。如有偏差请说明", task_id=task_id)
9. 张三确认符合方案 → update_task(task_id, status="pending_confirmation", summary="登录页面已优化完成，验收通过")
10. 回复老板: "登录页面优化已完成，已与员工验收确认，请确认。"
"""


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
        for i, line in enumerate(result_lines[:20]):
            print(f"  {DIM}│{RESET} {line[:58]}")
        if len(result_lines) > 20:
            print(f"  {DIM}│{RESET} {DIM}... ({len(result_lines) - 20} more lines){RESET}")
        print(f"  {DIM}└{'─' * 60}┘{RESET}")

    return {
        "type": "tool_result",
        "tool_use_id": block["id"],
        "content": result,
    }


def _agent_loop_stream(messages, system_prompt, debug_mode, for_cto=False):
    """流式调用 API，返回 content_blocks。"""
    first_chunk = True
    content_blocks = None
    try:
        stream_iter = call_api_stream(messages, system_prompt, for_cto=for_cto)
        for event_type, data in stream_iter:
            if event_type == "text_delta":
                if first_chunk:
                    print(f"\n  {CYAN}●{RESET} ", end="", flush=True)
                    first_chunk = False
                _stream_text(data)
            elif event_type == "content_blocks":
                content_blocks = data
                if not first_chunk:
                    print()
            elif event_type == "error":
                print(f"\n  {RED}{BOLD}✖ API Error:{RESET} {RED}{data}{RESET}")
                return []
    except Exception as e:
        print(f"\n  {RED}流式请求中断，回退到普通模式: {e}{RESET}")
        return None
    return content_blocks or []



def _agent_loop(messages, system_prompt, debug_mode=False, stream=True, for_cto=False):
    """持续调用 API 直到没有工具调用为止。"""
    while True:
        if stream:
            content_blocks = _agent_loop_stream(messages, system_prompt, debug_mode, for_cto=for_cto)
            if content_blocks is None:
                response = call_api(messages, system_prompt, for_cto=for_cto)
                content_blocks = response.get("content", [])
                for block in content_blocks:
                    if block["type"] == "text":
                        _handle_text_block(block)
        else:
            response = call_api(messages, system_prompt, for_cto=for_cto)
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


def _build_cto_system_prompt(base_prompt, state):
    """构建 CTO 的系统提示，包含员工信息和老板要求。"""
    roles = state.list_roles()
    workers = [r for r in roles if r["type"] == "worker"]
    
    worker_info = []
    for w in workers:
        info = f"- {w['name']}"
        if w.get("project_path"):
            info += f" (项目: {w['project_path']})"
        if w.get("context"):
            info += f" - {w['context'][:100]}"
        worker_info.append(info)
    
    workers_section = ""
    if worker_info:
        workers_section = f"\n\n## 当前员工列表\n\n" + "\n".join(worker_info)
    
    # 注入老板要求
    directives_section = ""
    directives_text = state.get_active_directives_text()
    if directives_text:
        directives_section = (
            "\n\n## ⚠️ 老板要求（必须遵守）\n\n"
            "以下是老板明确提出的要求和偏好，制定方案和分配任务时**必须**结合这些要求：\n\n"
            f"{directives_text}\n\n"
            "**注意**：每次方案讨论和任务分配都要检查是否符合以上要求。"
        )
    
    return base_prompt + CTO_SYSTEM_PROMPT + workers_section + directives_section


def _print_role_list(state):
    """打印角色列表。"""
    roles = state.list_roles()
    print(f"\n  {CYAN}组织架构:{RESET}")
    for r in roles:
        type_cn = {"boss": "👔 老板", "cto": "🧠 CTO", "worker": "👨‍💻"}.get(r["type"], "角色")
        path_info = ""
        if r["type"] == "worker":
            path_status = "✓" if r.get("path_exists") or not r.get("project_path") else "✗"
            path_info = f" {DIM}路径:{path_status}{RESET}"
        print(f"  {type_cn} {BOLD}{r['name']}{RESET}{path_info}")
    print()


def _print_task_list(state):
    """打印任务列表。"""
    tasks = state.list_tasks()
    status_cn = {
        "pending": "待处理", "analyzing": "分析中", "assigned": "已分配",
        "running": "进行中", "pending_confirmation": "待确认", 
        "completed": "已完成", "cancelled": "已取消"
    }
    status_color = {
        "pending": DIM, "analyzing": YELLOW, "assigned": CYAN,
        "running": BLUE, "pending_confirmation": GREEN, 
        "completed": GREEN, "cancelled": RED
    }
    print(f"\n  {CYAN}任务列表:{RESET}")
    for t in tasks[:10]:
        status = status_cn.get(t["status"], t["status"])
        color = status_color.get(t["status"], RESET)
        subtask_count = len(t.get("subtasks", []))
        completed = len([s for s in t.get("subtasks", []) if s.get("status") == "completed"])
        progress = f"{completed}/{subtask_count}" if subtask_count > 0 else "-"
        print(f"  {BOLD}{t['title'][:40]}{RESET} [{color}{status}{RESET}] 子任务:{progress}")
    if len(tasks) > 10:
        print(f"  {DIM}... 还有 {len(tasks) - 10} 个任务{RESET}")
    print()


def run():
    """应用入口：打印 Banner，进入交互循环。"""
    print_banner()

    # 初始化工作台状态
    from .workbench_state import WorkbenchState
    state = WorkbenchState(os.getcwd())
    
    # 注册全局状态（供工具访问）
    from .tools import register_state
    register_state(state)

    # 确保有 CTO
    cto = state.get_cto()
    if not cto:
        # 创建默认 CTO
        state.add_role({
            "type": "cto",
            "name": "CTO",
            "rules": [],
            "context": "负责接收老板指令，分配任务给员工"
        })
        cto = state.get_cto()

    # 初始化 Dashboard 服务
    dashboard_url = None
    try:
        from .dashboard_server import LocalDashboardServer
        dashboard = LocalDashboardServer(state)
        dashboard_url = dashboard.start()
        print(f"  {DIM}📊 Dashboard API: {dashboard_url}{RESET}")
        print(f"  {DIM}🎨 React 前端: cd web && npm run dev{RESET}\n")
    except Exception as e:
        print(f"  {YELLOW}⚠ Dashboard 启动失败: {e}{RESET}\n")

    # 初始化 MCP
    try:
        from .mcp_client import init_mcp
        init_mcp()
    except:
        pass

    messages = []
    base_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(cwd=os.getcwd(), platform=get_platform())
    debug_mode = False
    stream_mode = [STREAM_MODE]

    print(f"  {GREEN}💡 你是老板，输入指令会发给 CTO 处理{RESET}")
    print(f"  {DIM}   CTO 会判断是任务还是闲聊，并协调员工执行{RESET}\n")

    while True:
        try:
            print(separator("heavy"))
            # 用户固定为老板
            user_input = input(f"  {BOLD}{MAGENTA}[老板]{RESET} {BLUE}▶ {RESET}").strip()
            if not user_input:
                continue

            # 退出命令
            if user_input in ("/q", "exit"):
                print(f"\n  {DIM}👋 Bye!{RESET}\n")
                try:
                    from .mcp_client import get_mcp_manager
                    get_mcp_manager().shutdown()
                except:
                    pass
                break

            # 清空对话
            if user_input == "/c":
                messages = []
                print(f"\n  {GREEN}✓ 对话已清空{RESET}\n")
                continue

            # Debug 模式
            if user_input == "/debug":
                debug_mode = not debug_mode
                status = f"{GREEN}开启{RESET}" if debug_mode else f"{DIM}关闭{RESET}"
                print(f"\n  {YELLOW}🐛 Debug 模式已{status}{RESET}\n")
                continue

            # 流式输出
            if user_input == "/stream":
                stream_mode[0] = not stream_mode[0]
                status = f"{GREEN}开启{RESET}" if stream_mode[0] else f"{DIM}关闭{RESET}"
                print(f"\n  {CYAN}📡 流式输出已{status}{RESET}\n")
                continue

            # MCP 工具列表
            if user_input == "/mcp":
                try:
                    from .mcp_client import get_mcp_manager
                    m = get_mcp_manager()
                    if not m.clients:
                        print(f"\n  {DIM}No MCP servers running{RESET}\n")
                    else:
                        for name, client in m.clients.items():
                            print(f"\n  {CYAN}{BOLD}{name}{RESET} ({len(client.tools)} tools)")
                            for t in client.tools:
                                desc = t.get("description", "")[:60]
                                print(f"  {DIM}  - {t['name']}{RESET}  {desc}")
                        print()
                except Exception as e:
                    print(f"\n  {RED}MCP error: {e}{RESET}\n")
                continue

            # === 工作台命令 ===

            # 角色列表
            if user_input in ("/roles", "/角色", "/org"):
                _print_role_list(state)
                continue

            # 任务列表
            if user_input in ("/tasks", "/任务"):
                _print_task_list(state)
                continue

            # 查看任务详情
            if user_input.startswith("/task "):
                task_id = user_input[6:].strip()
                task = state.get_task(task_id)
                if not task:
                    # 尝试用标题搜索
                    tasks = state.list_tasks()
                    for t in tasks:
                        if task_id.lower() in t["title"].lower():
                            task = t
                            break
                if not task:
                    print(f"\n  {RED}未找到任务: {task_id}{RESET}\n")
                    continue
                
                print(f"\n  {CYAN}任务详情:{RESET}")
                print(f"  {BOLD}ID:{RESET} {task['id']}")
                print(f"  {BOLD}标题:{RESET} {task['title']}")
                print(f"  {BOLD}状态:{RESET} {task['status']}")
                print(f"  {BOLD}描述:{RESET} {task.get('description', '-')[:100]}")
                
                subtasks = task.get("subtasks", [])
                if subtasks:
                    print(f"  {BOLD}子任务:{RESET}")
                    for st in subtasks:
                        worker = state.get_role(st.get("worker_id", ""))
                        worker_name = worker["name"] if worker else "未知"
                        status_cn = {"pending": "待处理", "running": "进行中", "completed": "已完成", "failed": "失败"}
                        print(f"    - [{status_cn.get(st['status'], st['status'])}] {worker_name}: {st['content'][:50]}")
                
                conversation = task.get("conversation", [])
                if conversation:
                    print(f"  {BOLD}对话记录:{RESET} {len(conversation)} 条")
                print()
                continue

            # 确认完成任务
            if user_input.startswith("/confirm "):
                task_id = user_input[9:].strip()
                task = state.get_task(task_id)
                if not task:
                    print(f"\n  {RED}未找到任务: {task_id}{RESET}\n")
                    continue
                
                if task["status"] != "pending_confirmation":
                    print(f"\n  {YELLOW}任务状态不是待确认，当前状态: {task['status']}{RESET}\n")
                    continue
                
                state.update_task(task_id, {"status": "completed"})
                print(f"\n  {GREEN}✓ 任务已确认完成: {task['title']}{RESET}\n")
                continue

            # 当前状态
            if user_input in ("/status", "/状态"):
                cto = state.get_cto()
                workers = [r for r in state.list_roles() if r["type"] == "worker"]
                tasks = state.list_tasks()
                running_tasks = [t for t in tasks if t["status"] == "running"]
                pending_confirm = [t for t in tasks if t["status"] == "pending_confirmation"]
                
                print(f"\n  {CYAN}当前状态:{RESET}")
                print(f"  {BOLD}你的角色:{RESET} 老板")
                print(f"  {BOLD}CTO:{RESET} {cto['name'] if cto else '未配置'}")
                print(f"  {BOLD}员工数:{RESET} {len(workers)}")
                print(f"  {BOLD}进行中任务:{RESET} {len(running_tasks)}")
                if pending_confirm:
                    print(f"  {GREEN}{BOLD}待确认任务:{RESET} {len(pending_confirm)}{RESET}")
                    for t in pending_confirm:
                        print(f"    - {t['title']} (ID: {t['id']})")
                print()
                continue

            # 打开 Dashboard
            if user_input in ("/dashboard", "/web", "/面板"):
                if dashboard_url:
                    print(f"\n  {GREEN}✓ Dashboard API: {dashboard_url}{RESET}")
                    print(f"  {GREEN}✓ React 前端: cd web && npm run dev{RESET}\n")
                    webbrowser.open(dashboard_url)
                else:
                    print(f"\n  {RED}Dashboard 未启动{RESET}\n")
                continue

            # 帮助
            if user_input == "/help":
                print(f"\n  {CYAN}可用命令:{RESET}")
                print(f"  {DIM}/q, exit{RESET}        - 退出程序")
                print(f"  {DIM}/c{RESET}              - 清空对话")
                print(f"  {DIM}/debug{RESET}          - 切换 Debug 模式")
                print(f"  {DIM}/stream{RESET}         - 切换流式输出")
                print(f"  {DIM}/mcp{RESET}            - 查看 MCP 工具列表")
                print(f"  {MAGENTA}/roles{RESET}           - 查看组织架构")
                print(f"  {MAGENTA}/tasks{RESET}           - 查看任务列表")
                print(f"  {MAGENTA}/task <任务ID>{RESET}   - 查看任务详情")
                print(f"  {GREEN}/confirm <任务ID>{RESET}  - 确认完成任务")
                print(f"  {MAGENTA}/status{RESET}          - 查看当前状态")
                print(f"  {MAGENTA}/dashboard{RESET}       - 打开 Dashboard")
                print(f"  {DIM}/help{RESET}           - 显示此帮助信息")
                print()
                continue

            # ===== 核心：老板指令发给 CTO =====
            print(separator("dot"))
            print(f"  {DIM}📨 发送给 CTO...{RESET}")

            # 构建 CTO 的系统提示（包含员工信息）
            cto_system_prompt = _build_cto_system_prompt(base_system_prompt, state)

            messages.append({"role": "user", "content": user_input})
            _agent_loop(messages, cto_system_prompt, debug_mode, stream_mode[0], for_cto=True)
            print()

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {DIM}👋 Bye!{RESET}\n")
            break
        except Exception as err:
            print(f"\n  {RED}{BOLD}✖ Error:{RESET} {RED}{err}{RESET}\n")
