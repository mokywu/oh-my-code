"""内置工具实现与注册。聚合各工具模块。"""

from .tool_file import tool_edit, tool_glob, tool_grep, tool_read, tool_write
from .tool_shell import tool_bash
from .tool_web import tool_browse, tool_search
from .tool_fs import get_platform, tool_fs
from .tool_mcp import tool_mcp
from .tool_task import (
    tool_create_task,
    tool_update_task,
    tool_add_subtask,
    tool_update_subtask,
    tool_log_conversation,
    tool_get_task_status,
)


# ==================== 全局状态 ====================
# 用于跨模块访问 WorkbenchState（在 agent.py 启动时注册）

_global_state = None


def register_state(state):
    """注册全局状态对象。"""
    global _global_state
    _global_state = state


def get_state():
    """获取全局状态对象。"""
    return _global_state


# ==================== 询问员工工具 ====================

def tool_ask_worker(args):
    """CTO 询问员工，返回员工的回复。
    
    员工可以有两种工作模式：
    1. LLM 模式：调用 API 获取回复（默认）
    2. Claude CLI 模式：调用 claude 命令在项目目录执行任务
    """
    global _global_state
    
    if not _global_state:
        return "error: WorkbenchState not initialized"
    
    worker_name = args.get("worker", "").strip()
    question = args.get("question", "").strip()
    task_id = args.get("task_id", "").strip()
    
    if not worker_name:
        return "error: missing 'worker' parameter"
    if not question:
        return "error: missing 'question' parameter"
    
    # 查找员工
    workers = [r for r in _global_state.list_roles() if r["type"] == "worker"]
    target = None
    for w in workers:
        if w["name"].lower() == worker_name.lower() or w["id"] == worker_name:
            target = w
            break
    
    if not target:
        available = ", ".join(w["name"] for w in workers) or "(无员工)"
        return f"error: 员工 '{worker_name}' 不存在。可用员工: {available}"

    # 优先使用显式 task_id；未提供时尝试推断当前活跃任务
    bind_task_id = task_id
    if bind_task_id:
        if not _global_state.get_task(bind_task_id):
            return f"error: task '{bind_task_id}' not found"
    else:
        active_statuses = {"pending", "analyzing", "assigned", "running", "pending_confirmation"}
        active_tasks = [t for t in _global_state.list_tasks() if t.get("status") in active_statuses]
        if active_tasks:
            bind_task_id = active_tasks[0]["id"]
    
    # 检查员工是否使用 Claude CLI 模式
    use_claude_cli = target.get("use_claude_cli", False)
    result = _ask_worker_claude_cli(target, question) if use_claude_cli else _ask_worker_llm(target, question)

    # 自动记录 CTO 与员工对话到任务日志
    if bind_task_id:
        try:
            cto = _global_state.get_cto() or {}
            cto_id = cto.get("id", "role-cto-001")
            _global_state.add_conversation(bind_task_id, cto_id, f"[to:{target['name']}] {question}")
            _global_state.add_conversation(bind_task_id, target["id"], result)
        except Exception:
            # 记录失败不影响主流程
            pass

    return result



def _ask_worker_claude_cli(worker, question):
    """使用 Claude CLI 模式执行任务。

    流程：
    1. 如果 CLAUDE_SKIP_PERMISSIONS=true 且无需审批 → 直接执行
    2. 否则 → 创建审批请求，轮询等待老板在 Web 页面确认后执行
    """
    import subprocess
    import os
    import time
    from .config import DEBUG_MODE, CLAUDE_SKIP_PERMISSIONS

    project_path = worker.get("project_path", os.getcwd())

    if not os.path.exists(project_path):
        return f"error: 项目路径不存在: {project_path}"

    # 检测是否需要写入操作（关键词匹配）
    write_keywords = ["修改", "写入", "保存", "创建文件", "编辑", "删除",
                       "modify", "write", "save", "edit", "create", "delete",
                       "改为", "替换", "更新", "add", "remove", "update"]
    needs_write = any(kw in question.lower() for kw in write_keywords)

    # 决定是否需要审批
    need_approval = needs_write and not CLAUDE_SKIP_PERMISSIONS

    if need_approval and _global_state:
        # 寻找关联的活跃任务 ID
        active_statuses = {"pending", "analyzing", "assigned", "running"}
        active_tasks = [t for t in _global_state.list_tasks() if t.get("status") in active_statuses]
        task_id = active_tasks[0]["id"] if active_tasks else ""

        command_preview = f"claude --print --dangerously-skip-permissions '{question[:120]}...'"
        approval = _global_state.create_approval(
            worker_id=worker["id"],
            worker_name=worker["name"],
            task_id=task_id,
            description=question[:200],
            command_preview=command_preview,
        )

        print(f"\n  ⏳ 等待老板在 Web 页面审批（审批ID: {approval['id']}）...")
        print(f"  📋 请打开 Dashboard → 权限审批 → 点击「批准」")

        # 轮询等待审批结果（最多等 5 分钟）
        approval_id = approval["id"]
        poll_start = time.time()
        poll_timeout = 300  # 5分钟

        while time.time() - poll_start < poll_timeout:
            time.sleep(2)
            current = _global_state.get_approval(approval_id)
            if not current:
                return f"[{worker['name']}]: error: 审批请求丢失"
            if current["status"] == "approved":
                print(f"  ✅ 老板已批准，开始执行...")
                break
            if current["status"] == "rejected":
                return f"[{worker['name']}]: 老板拒绝了此次执行请求。"
        else:
            return f"[{worker['name']}]: error: 审批超时（5分钟内未获得批准）"

    # 构建 Claude CLI 命令
    env = os.environ.copy()
    env["OH_MY_CODE_WORKER_PROMPT"] = question

    # 审批通过或已开启全局跳过权限 → 带上 skip-permissions
    use_skip = CLAUDE_SKIP_PERMISSIONS or (need_approval)
    permission_flag = " --dangerously-skip-permissions" if use_skip else ""
    ps_script = (
        "if (Test-Path $PROFILE) { . $PROFILE }; "
        "Set-Location -Path $PWD; "
        f"claude --print{permission_flag} $env:OH_MY_CODE_WORKER_PROMPT"
    )
    cmd = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
    ]

    if DEBUG_MODE:
        print(f"\n  [DEBUG] 通过 PowerShell 执行 claude 命令:")
        print(f"  [DEBUG]   目录: {project_path}")
        mode = "skip-permissions" if use_skip else "require-approval"
        print(f"  [DEBUG]   命令: claude --print{permission_flag} '{question[:80]}{'...' if len(question) > 80 else ''}'")
        print(f"  [DEBUG]   权限模式: {mode}")
        print("  [DEBUG]   认证方式: 使用当前机器已有的 Claude shell 环境")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )

        elapsed = time.time() - start_time
        output = result.stdout.strip()
        error = result.stderr.strip()

        if DEBUG_MODE:
            print(f"\n  [DEBUG] 执行完成 ({elapsed:.1f}s)")
            print(f"  [DEBUG] 返回码: {result.returncode}")
            if output:
                output_lines = output.split("\n")
                print(f"  [DEBUG] stdout ({len(output)} 字符):")
                for line in output_lines[:10]:
                    print(f"  [DEBUG]   {line[:100]}")
                if len(output_lines) > 10:
                    print(f"  [DEBUG]   ... 还有 {len(output_lines) - 10} 行")
            if error:
                print(f"  [DEBUG] stderr: {error[:500]}")

        combined = f"{output}\n{error}".lower()
        if "failed to authenticate" in combined or "api error: 401" in combined:
            return (
                f"[{worker['name']}]: {output or error}\n"
                "提示：检测到 Claude 401 认证失败。程序已尝试加载 PowerShell profile。"
                "请确认你平时可用的终端与这里是同一个 profile（$PROFILE），"
                "并在同一 PowerShell 中测试：claude --print \"ping\"。"
            )

        if result.returncode != 0 and not output:
            return (
                f"[{worker['name']}]: error: {error or 'claude 命令执行失败'}\n"
                "提示：当前是通过 PowerShell 调用 claude。"
                "如果你在自己终端里可用，但这里不可用，通常是因为你的 shell profile / alias / function "
                "与 Python 进程启动的 PowerShell 环境仍有差异。"
            )

        return f"[{worker['name']}]: {output}"

    except subprocess.TimeoutExpired:
        return f"[{worker['name']}]: error: 任务执行超时（5分钟）"
    except FileNotFoundError:
        return f"[{worker['name']}]: error: powershell 或 claude 命令未找到，请确认本机命令行可直接运行 claude"
    except Exception as e:
        return f"[{worker['name']}]: error: {e}"


def _ask_worker_llm(worker, question):
    """使用 LLM API 模式获取回复。"""
    from .config import API_KEY, API_URL, MODEL, SYSTEM_PROMPT_TEMPLATE, MAX_TOKENS
    from .api import call_api
    import os
    
    # 使用员工的配置或默认配置
    worker_api_key = worker.get("api_key") or API_KEY
    worker_model = worker.get("model") or MODEL
    worker_api_url = worker.get("api_url") or API_URL
    
    # 构建系统提示
    base_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        cwd=worker.get("project_path") or os.getcwd(),
        platform=get_platform()
    )
    
    extra_parts = []
    if worker.get("rules"):
        rules_text = "\n".join(f"- {r}" for r in worker["rules"])
        extra_parts.append(f"<role_rules>\n{rules_text}\n</role_rules>")
    
    if worker.get("context"):
        extra_parts.append(f"<role_context>\n{worker['context']}\n</role_context>")
    
    if worker.get("project_path"):
        extra_parts.append(f"<project_path>\n{worker['project_path']}\n</project_path>")
    
    if worker.get("system_prompt"):
        extra_parts.append(f"<custom_prompt>\n{worker['system_prompt']}\n</custom_prompt>")
    
    worker_prompt = base_prompt
    if extra_parts:
        worker_prompt += f"\n\n[员工: {worker['name']}]\n" + "\n".join(extra_parts)
    
    # 添加简洁回复指示
    worker_prompt += "\n\n[重要] 请简洁回复，直接回答问题，不要过度展开。"
    
    # 调用员工的 LLM（不使用工具，只获取文本回复）
    try:
        response = call_api(
            [{"role": "user", "content": question}],
            worker_prompt,
            api_key=worker_api_key,
            model=worker_model,
            api_url=worker_api_url,
            max_tokens=2048,  # 限制回复长度
            tools=[],  # 不使用工具
        )
        
        # 提取回复文本
        content = response.get("content", [])
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        if text_parts:
            full_response = "\n".join(text_parts)
            return f"[{worker['name']}]: {full_response}"
        else:
            return f"[{worker['name']}]: (无文本回复)"
            
    except Exception as e:
        return f"error: 调用 {worker['name']} 失败: {e}"


def tool_list_workers(args):
    """列出所有员工。"""
    global _global_state
    
    if not _global_state:
        return "error: WorkbenchState not initialized"
    
    workers = [r for r in _global_state.list_roles() if r["type"] == "worker"]
    
    if not workers:
        return "当前没有员工。请在 Web Dashboard 添加员工。"
    
    lines = ["员工列表:"]
    for w in workers:
        path = w.get("project_path", "")
        path_info = f" (项目: {path})" if path else ""
        lines.append(f"- {w['name']}{path_info}")
    
    return "\n".join(lines)


# ==================== 工具注册表 ====================

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
    "fs": (
        "File system operations (cross-platform). action: list|copy|move|delete|mkdir. "
        "list: path?, recursive? | copy: src, dst, overwrite? | move: src, dst | delete: path | mkdir: path, exist_ok?",
        {
            "action": "string",
            "path": "string?",
            "src": "string?",
            "dst": "string?",
            "recursive": "boolean?",
            "overwrite": "boolean?",
            "exist_ok": "boolean?",
        },
        tool_fs,
    ),
    "mcp": (
        "MCP tool management",
        {"action": "string?", "server": "string?", "tool": "string?", "arguments": "object?"},
        tool_mcp,
    ),
    # === 组织架构工具 ===
    "list_workers": (
        "List all workers (employees) in the organization",
        {},
        tool_list_workers,
    ),
    "ask_worker": (
        "Ask a specific worker a question. Worker will respond using their LLM configuration. "
        "Use this to communicate with employees about tasks.",
        {"worker": "string", "question": "string"},
        tool_ask_worker,
    ),
    # === 任务管理工具 ===
    "create_task": (
        "Create a new task. Returns task_id.",
        {"title": "string", "description": "string?"},
        tool_create_task,
    ),
    "update_task": (
        "Update task status. Status: pending|analyzing|assigned|running|pending_confirmation|completed|cancelled",
        {"task_id": "string", "status": "string", "summary": "string?"},
        tool_update_task,
    ),
    "add_subtask": (
        "Add a subtask and assign to a worker.",
        {"task_id": "string", "worker_id": "string?", "worker_name": "string?", "content": "string"},
        tool_add_subtask,
    ),
    "update_subtask": (
        "Update subtask status. Status: pending|running|completed|failed",
        {"task_id": "string", "subtask_id": "string", "status": "string", "result": "string?"},
        tool_update_subtask,
    ),
    "log_conversation": (
        "Log a conversation message to the task.",
        {"task_id": "string", "speaker": "string", "message": "string"},
        tool_log_conversation,
    ),
    "get_task_status": (
        "Get task status. If task_id not provided, returns all tasks summary.",
        {"task_id": "string?"},
        tool_get_task_status,
    ),
}



def run_tool(name, args):
    """执行指定工具，捕获异常返回错误信息。"""
    # 内置工具
    if name in TOOLS:
        try:
            return TOOLS[name][2](args)
        except Exception as err:
            return f"error: {err}"
    
    # MCP 工具 (格式: mcp__server__tool)
    if name.startswith("mcp__"):
        try:
            from .mcp_client import get_mcp_manager
            m = get_mcp_manager()
            resolved = m.resolve_tool(name)
            if resolved:
                server, tool = resolved
                return m.call(server, tool, args)
            return f"error: unknown MCP tool: {name}"
        except Exception as err:
            return f"error: {err}"
    
    return f"error: 未知工具 '{name}'"



# CTO 可用的工具（只负责任务分配，不执行具体工作）
CTO_TOOLS = {
    "list_workers",
    "ask_worker",
    "create_task",
    "update_task",
    "add_subtask",
    "update_subtask",
    "log_conversation",
    "get_task_status",
}


def make_schema(for_cto=False):
    """将工具注册表转换为 Anthropic API tools schema 格式。
    
    Args:
        for_cto: 如果为 True，只返回 CTO 可用的工具（任务管理相关）
    """
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        # CTO 只能使用任务管理工具
        if for_cto and name not in CTO_TOOLS:
            continue
            
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
    
    # CTO 不使用 MCP 工具
    if not for_cto:
        # 添加 MCP 工具
        try:
            from .mcp_client import get_mcp_manager
            result.extend(get_mcp_manager().get_tools())
        except:
            pass
    
    return result

