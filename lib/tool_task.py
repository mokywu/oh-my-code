"""任务管理工具：CTO 用于创建和管理任务。"""

from __future__ import annotations

import json
from typing import Any


def tool_create_task(args: dict[str, Any]) -> str:
    """创建新任务。"""
    from .tools import get_state
    
    state = get_state()
    if not state:
        return "error: WorkbenchState not initialized"
    
    title = args.get("title", "").strip()
    description = args.get("description", "").strip()
    
    if not title:
        return "error: missing 'title' parameter"
    
    # 获取 CTO ID
    cto = state.get_cto()
    cto_id = cto["id"] if cto else ""
    
    task = state.add_task({
        "title": title,
        "description": description,
        "creator_id": cto_id,
    })
    
    return json.dumps({
        "success": True,
        "task_id": task["id"],
        "message": f"任务 '{title}' 已创建，ID: {task['id']}"
    }, ensure_ascii=False)


def tool_update_task(args: dict[str, Any]) -> str:
    """更新任务状态。"""
    from .tools import get_state
    
    state = get_state()
    if not state:
        return "error: WorkbenchState not initialized"
    
    task_id = args.get("task_id", "").strip()
    status = args.get("status", "").strip()
    summary = args.get("summary", "").strip()
    
    if not task_id:
        return "error: missing 'task_id' parameter"
    if not status:
        return "error: missing 'status' parameter"
    
    valid_statuses = ["pending", "analyzing", "assigned", "running", "pending_confirmation", "completed", "cancelled"]
    if status not in valid_statuses:
        return f"error: invalid status '{status}'. Valid: {', '.join(valid_statuses)}"
    
    task = state.get_task(task_id)
    if not task:
        return f"error: task '{task_id}' not found"
    
    updates = {"status": status}
    if summary:
        updates["summary"] = summary
    
    state.update_task(task_id, updates)
    
    return json.dumps({
        "success": True,
        "task_id": task_id,
        "status": status,
        "message": f"任务状态已更新为: {status}"
    }, ensure_ascii=False)


def tool_add_subtask(args: dict[str, Any]) -> str:
    """添加子任务。"""
    from .tools import get_state
    
    state = get_state()
    if not state:
        return "error: WorkbenchState not initialized"
    
    task_id = args.get("task_id", "").strip()
    worker_id = args.get("worker_id", "").strip()
    worker_name = args.get("worker_name", "").strip()
    content = args.get("content", "").strip()
    
    if not task_id:
        return "error: missing 'task_id' parameter"
    if not content:
        return "error: missing 'content' parameter"
    if not worker_id and not worker_name:
        return "error: missing 'worker_id' or 'worker_name' parameter"
    
    # 查找员工
    if worker_name and not worker_id:
        workers = [r for r in state.list_roles() if r["type"] == "worker"]
        for w in workers:
            if w["name"].lower() == worker_name.lower():
                worker_id = w["id"]
                break
    
    if not worker_id:
        return f"error: worker '{worker_name}' not found"
    
    task = state.get_task(task_id)
    if not task:
        return f"error: task '{task_id}' not found"
    
    subtask = state.add_subtask(task_id, {
        "worker_id": worker_id,
        "content": content,
    })
    
    return json.dumps({
        "success": True,
        "subtask_id": subtask["id"],
        "task_id": task_id,
        "worker_id": worker_id,
        "message": f"子任务已添加，分配给员工 {worker_id}"
    }, ensure_ascii=False)


def tool_update_subtask(args: dict[str, Any]) -> str:
    """更新子任务状态。"""
    from .tools import get_state
    
    state = get_state()
    if not state:
        return "error: WorkbenchState not initialized"
    
    task_id = args.get("task_id", "").strip()
    subtask_id = args.get("subtask_id", "").strip()
    status = args.get("status", "").strip()
    result = args.get("result", "").strip()
    
    if not task_id or not subtask_id:
        return "error: missing 'task_id' or 'subtask_id' parameter"
    if not status:
        return "error: missing 'status' parameter"
    
    valid_statuses = ["pending", "running", "completed", "failed"]
    if status not in valid_statuses:
        return f"error: invalid status '{status}'. Valid: {', '.join(valid_statuses)}"
    
    state.update_subtask(task_id, subtask_id, {
        "status": status,
        "result": result,
    })
    
    return json.dumps({
        "success": True,
        "subtask_id": subtask_id,
        "status": status,
        "message": f"子任务状态已更新为: {status}"
    }, ensure_ascii=False)


def tool_log_conversation(args: dict[str, Any]) -> str:
    """记录对话到任务日志。"""
    from .tools import get_state
    from datetime import datetime, timezone
    
    state = get_state()
    if not state:
        return "error: WorkbenchState not initialized"
    
    task_id = args.get("task_id", "").strip()
    speaker = args.get("speaker", "").strip()
    message = args.get("message", "").strip()
    
    if not task_id:
        return "error: missing 'task_id' parameter"
    if not speaker or not message:
        return "error: missing 'speaker' or 'message' parameter"
    
    task = state.get_task(task_id)
    if not task:
        return f"error: task '{task_id}' not found"
    
    # 添加对话记录
    conversation = task.get("conversation", [])
    conversation.append({
        "speaker": speaker,
        "message": message,
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    })
    
    state.update_task(task_id, {"conversation": conversation})
    
    return json.dumps({
        "success": True,
        "message": "对话已记录"
    }, ensure_ascii=False)


def tool_get_task_status(args: dict[str, Any]) -> str:
    """获取任务状态详情。"""
    from .tools import get_state
    
    state = get_state()
    if not state:
        return "error: WorkbenchState not initialized"
    
    task_id = args.get("task_id", "").strip()
    
    if not task_id:
        # 返回所有任务摘要
        tasks = state.list_tasks()
        if not tasks:
            return json.dumps({"tasks": [], "message": "当前没有任务"}, ensure_ascii=False)
        
        summaries = []
        for t in tasks:
            subtasks = t.get("subtasks", [])
            completed = len([s for s in subtasks if s.get("status") == "completed"])
            summaries.append({
                "id": t["id"],
                "title": t["title"],
                "status": t["status"],
                "subtask_count": len(subtasks),
                "completed_subtasks": completed,
            })
        
        return json.dumps({"tasks": summaries}, ensure_ascii=False)
    
    task = state.get_task(task_id)
    if not task:
        return f"error: task '{task_id}' not found"
    
    # 返回详细任务信息
    result = {
        "id": task["id"],
        "title": task["title"],
        "description": task.get("description", ""),
        "status": task["status"],
        "subtasks": [],
        "conversation_count": len(task.get("conversation", [])),
    }
    
    # 子任务摘要
    for st in task.get("subtasks", []):
        worker = state.get_role(st.get("worker_id", ""))
        result["subtasks"].append({
            "id": st["id"],
            "worker_name": worker["name"] if worker else "未知",
            "content": st.get("content", "")[:100],
            "status": st.get("status", "pending"),
        })
    
    return json.dumps(result, ensure_ascii=False, indent=2)
