"""工作台状态存储：组织架构、角色、任务、进度。"""

from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = value.splitlines()
    elif isinstance(value, list):
        items = value
    else:
        items = [str(value)]
    return [str(item).strip() for item in items if str(item).strip()]


class WorkbenchState:
    """负责维护工作台持久化数据。"""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.data_dir = os.path.join(self.root_dir, ".oh_my_code")
        self.state_file = os.path.join(self.data_dir, "workbench_state.json")
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {}
        self.load()

    # ==================== 数据结构 ====================

    def _make_role(self, role_type: str, name: str) -> dict[str, Any]:
        current_time = _now()
        return {
            "id": f"role-{uuid.uuid4().hex[:8]}",
            "type": role_type,  # boss, cto, worker
            "name": name.strip(),
            "project_path": "",  # 仅 worker 使用
            "rules": [],
            "context": "",
            "api_key": "",  # 每个角色独立配置
            "system_prompt": "",
            "model": "",
            "created_at": current_time,
            "updated_at": current_time,
        }

    def _make_task(self, title: str, creator_id: str) -> dict[str, Any]:
        current_time = _now()
        return {
            "id": f"task-{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "description": "",
            "status": "pending",  # pending, analyzing, assigned, running, pending_confirmation, completed, cancelled
            "creator_id": creator_id,  # CTO 的 ID
            "boss_id": "",  # 老板的 ID（可选）
            "subtasks": [],  # 子任务列表
            "conversation": [],  # 对话历史
            "summary": "",  # 任务摘要
            "created_at": current_time,
            "updated_at": current_time,
        }

    def _make_subtask(self, task_id: str, worker_id: str, content: str) -> dict[str, Any]:
        current_time = _now()
        return {
            "id": f"sub-{uuid.uuid4().hex[:8]}",
            "task_id": task_id,
            "worker_id": worker_id,
            "content": content,
            "status": "pending",  # pending, running, completed, failed
            "result": "",
            "conversation": [],
            "created_at": current_time,
            "updated_at": current_time,
        }

    def _make_directive(self, content: str, category: str = "general") -> dict[str, Any]:
        """创建一条老板要求/偏好记录。"""
        current_time = _now()
        return {
            "id": f"dir-{uuid.uuid4().hex[:8]}",
            "content": content.strip(),
            "category": category.strip() or "general",  # general, quality, style, process, tech
            "active": True,
            "created_at": current_time,
            "updated_at": current_time,
        }

    def _make_approval(self, worker_id: str, worker_name: str, task_id: str, description: str, command_preview: str) -> dict[str, Any]:
        """创建一个权限审批请求。"""
        current_time = _now()
        return {
            "id": f"appr-{uuid.uuid4().hex[:8]}",
            "worker_id": worker_id,
            "worker_name": worker_name,
            "task_id": task_id,
            "description": description,
            "command_preview": command_preview,
            "status": "pending",  # pending, approved, rejected
            "created_at": current_time,
            "resolved_at": "",
        }

    def _default_state(self) -> dict[str, Any]:
        current_time = _now()
        boss = self._make_role("boss", "老板")
        cto = self._make_role("cto", "CTO")
        return {
            "version": 2,
            "created_at": current_time,
            "updated_at": current_time,
            "roles": [boss, cto],
            "tasks": [],
            "recent_events": [],
            "pending_approvals": [],
            "boss_directives": [],
        }

    # ==================== 持久化 ====================

    def load(self) -> None:
        with self._lock:
            os.makedirs(self.data_dir, exist_ok=True)
            if not os.path.exists(self.state_file):
                self._state = self._default_state()
                self._append_event("system", "工作台已初始化")
                self._save_locked()
                return

            with open(self.state_file, "r", encoding="utf-8") as file:
                self._state = json.load(file)

            # 版本迁移
            if self._state.get("version", 1) < 2:
                self._migrate_from_v1()
                self._state["version"] = 2

            self._state.setdefault("roles", [])
            self._state.setdefault("tasks", [])
            self._state.setdefault("recent_events", [])
            self._state.setdefault("pending_approvals", [])
            self._state.setdefault("boss_directives", [])

            if not self._state["roles"]:
                self._state = self._default_state()
                self._append_event("system", "检测到空工作台，已重建默认角色")

            self._save_locked()

    def _migrate_from_v1(self) -> None:
        """从 v1 版本迁移数据。"""
        old_depts = self._state.pop("departments", [])
        roles = []
        for dept in old_depts:
            worker = self._make_role("worker", dept.get("name", "员工"))
            worker["project_path"] = dept.get("project_path", "")
            worker["rules"] = dept.get("rules", [])
            worker["context"] = dept.get("context", "")
            roles.append(worker)
        self._state["roles"] = roles
        self._state["tasks"] = []
        self._append_event("system", f"已从 v1 迁移 {len(roles)} 个员工")

    def _save_locked(self) -> None:
        self._state["updated_at"] = _now()
        with open(self.state_file, "w", encoding="utf-8") as file:
            json.dump(self._state, file, ensure_ascii=False, indent=2)

    def _append_event(self, kind: str, message: str, role_id: str = "", task_id: str = "") -> None:
        event = {
            "kind": kind,
            "message": message,
            "role_id": role_id,
            "task_id": task_id,
            "created_at": _now(),
        }
        self._state.setdefault("recent_events", []).insert(0, event)
        self._state["recent_events"] = self._state["recent_events"][:100]

    # ==================== 快照 ====================

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = copy.deepcopy(self._state)

        snapshot["root_dir"] = self.root_dir
        snapshot["state_file"] = self.state_file
        snapshot["generated_at"] = _now()

        # 为 worker 添加路径状态
        for role in snapshot.get("roles", []):
            if role["type"] == "worker":
                path = role.get("project_path", "")
                role["path_exists"] = bool(path and os.path.isdir(path))
                role["effective_path"] = path or self.root_dir

        # 统计信息
        workers = [r for r in snapshot.get("roles", []) if r["type"] == "worker"]
        tasks = snapshot.get("tasks", [])
        pending_approvals = [a for a in snapshot.get("pending_approvals", []) if a["status"] == "pending"]
        active_directives = [d for d in snapshot.get("boss_directives", []) if d.get("active", True)]
        snapshot["stats"] = {
            "worker_count": len(workers),
            "task_count": len(tasks),
            "pending_tasks": len([t for t in tasks if t["status"] == "pending"]),
            "running_tasks": len([t for t in tasks if t["status"] == "running"]),
            "completed_tasks": len([t for t in tasks if t["status"] == "completed"]),
            "pending_approvals": len(pending_approvals),
            "directive_count": len(active_directives),
        }

        return snapshot

    # ==================== 角色管理 ====================

    def list_roles(self, role_type: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            roles = copy.deepcopy(self._state.get("roles", []))
        if role_type:
            roles = [r for r in roles if r["type"] == role_type]
        return roles

    def get_role(self, role_id: str) -> dict[str, Any] | None:
        with self._lock:
            for role in self._state.get("roles", []):
                if role["id"] == role_id:
                    return copy.deepcopy(role)
        return None

    def get_boss(self) -> dict[str, Any] | None:
        with self._lock:
            for role in self._state.get("roles", []):
                if role["type"] == "boss":
                    return copy.deepcopy(role)
        return None

    def get_cto(self) -> dict[str, Any] | None:
        with self._lock:
            for role in self._state.get("roles", []):
                if role["type"] == "cto":
                    return copy.deepcopy(role)
        return None

    def add_worker(self, name: str) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("员工名称不能为空")

        with self._lock:
            worker = self._make_role("worker", clean_name)
            self._state["roles"].append(worker)
            self._append_event("config", f"新增员工：{clean_name}", role_id=worker["id"])
            self._save_locked()
            return copy.deepcopy(worker)

    def update_role(self, role_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            role = None
            for r in self._state["roles"]:
                if r["id"] == role_id:
                    role = r
                    break
            if not role:
                raise ValueError(f"未找到角色: {role_id}")

            # 可更新的字段
            if "name" in updates:
                name = str(updates["name"] or "").strip()
                if not name:
                    raise ValueError("名称不能为空")
                role["name"] = name

            if "project_path" in updates:
                path = str(updates.get("project_path", "")).strip()
                role["project_path"] = os.path.abspath(os.path.expanduser(path)) if path else ""

            if "rules" in updates:
                role["rules"] = _normalize_list(updates.get("rules"))

            if "context" in updates:
                role["context"] = str(updates.get("context", "")).strip()

            if "api_key" in updates:
                role["api_key"] = str(updates.get("api_key", "")).strip()

            if "system_prompt" in updates:
                role["system_prompt"] = str(updates.get("system_prompt", "")).strip()

            if "model" in updates:
                role["model"] = str(updates.get("model", "")).strip()

            role["updated_at"] = _now()
            self._append_event("config", f"更新角色配置：{role['name']}", role_id=role["id"])
            self._save_locked()
            return copy.deepcopy(role)

    def delete_role(self, role_id: str) -> None:
        with self._lock:
            role = None
            for i, r in enumerate(self._state["roles"]):
                if r["id"] == role_id:
                    role = r
                    self._state["roles"].pop(i)
                    break
            if not role:
                raise ValueError(f"未找到角色: {role_id}")
            if role["type"] in ("boss", "cto"):
                raise ValueError(f"不能删除 {role['type']} 角色")

            self._append_event("config", f"删除员工：{role['name']}", role_id=role["id"])
            self._save_locked()

    # ==================== 任务管理 ====================

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            tasks = copy.deepcopy(self._state.get("tasks", []))
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        # 按创建时间倒序
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        return tasks

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            for task in self._state.get("tasks", []):
                if task["id"] == task_id:
                    return copy.deepcopy(task)
        return None

    def create_task(self, title: str, description: str = "", creator_id: str = "") -> dict[str, Any]:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("任务标题不能为空")

        with self._lock:
            # 默认使用 CTO 作为创建者
            if not creator_id:
                for role in self._state["roles"]:
                    if role["type"] == "cto":
                        creator_id = role["id"]
                        break

            task = self._make_task(clean_title, creator_id)
            task["description"] = description.strip()
            self._state["tasks"].append(task)
            self._append_event("task", f"创建任务：{clean_title}", task_id=task["id"])
            self._save_locked()
            return copy.deepcopy(task)

    def add_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """添加任务（兼容工具调用）。"""
        title = task_data.get("title", "")
        description = task_data.get("description", "")
        creator_id = task_data.get("creator_id", "")
        return self.create_task(title, description, creator_id)

    def update_task(self, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            task = None
            for t in self._state["tasks"]:
                if t["id"] == task_id:
                    task = t
                    break
            if not task:
                raise ValueError(f"未找到任务: {task_id}")

            valid_statuses = {"pending", "analyzing", "assigned", "running", "pending_confirmation", "completed", "cancelled"}
            if "status" in updates:
                status = updates["status"]
                if status not in valid_statuses:
                    raise ValueError(f"非法状态: {status}")
                task["status"] = status

            if "title" in updates:
                task["title"] = str(updates["title"] or task["title"]).strip()

            if "description" in updates:
                task["description"] = str(updates.get("description", "")).strip()

            if "summary" in updates:
                task["summary"] = str(updates.get("summary", "")).strip()

            if "conversation" in updates:
                task["conversation"] = updates["conversation"]

            task["updated_at"] = _now()
            self._append_event("task", f"更新任务状态：{task['status']}", task_id=task["id"])
            self._save_locked()
            return copy.deepcopy(task)

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            for i, t in enumerate(self._state["tasks"]):
                if t["id"] == task_id:
                    task = self._state["tasks"].pop(i)
                    self._append_event("task", f"删除任务：{task['title']}", task_id=task["id"])
                    self._save_locked()
                    return
            raise ValueError(f"未找到任务: {task_id}")

    # ==================== 子任务管理 ====================

    def add_subtask(self, task_id: str, subtask_data: dict[str, Any] | str) -> dict[str, Any]:
        """添加子任务。支持 dict 或 (worker_id, content) 兼容。"""
        # 兼容旧签名 add_subtask(task_id, worker_id, content)
        if isinstance(subtask_data, str):
            # 旧签名：task_id, worker_id, content 在第三个参数
            raise ValueError("请使用 dict 格式调用 add_subtask")

        worker_id = subtask_data.get("worker_id", "")
        content = subtask_data.get("content", "")

        if not worker_id:
            raise ValueError("缺少 worker_id")
        if not content:
            raise ValueError("缺少 content")

        with self._lock:
            task = None
            for t in self._state["tasks"]:
                if t["id"] == task_id:
                    task = t
                    break
            if not task:
                raise ValueError(f"未找到任务: {task_id}")

            # 验证 worker 存在
            worker_exists = any(r["id"] == worker_id and r["type"] == "worker" for r in self._state["roles"])
            if not worker_exists:
                raise ValueError(f"未找到员工: {worker_id}")

            subtask = self._make_subtask(task_id, worker_id, content)
            task["subtasks"].append(subtask)
            task["updated_at"] = _now()

            self._append_event("task", f"分配子任务给员工", role_id=worker_id, task_id=task_id)
            self._save_locked()
            return copy.deepcopy(subtask)

    def update_subtask(self, task_id: str, subtask_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            task = None
            for t in self._state["tasks"]:
                if t["id"] == task_id:
                    task = t
                    break
            if not task:
                raise ValueError(f"未找到任务: {task_id}")

            subtask = None
            for st in task["subtasks"]:
                if st["id"] == subtask_id:
                    subtask = st
                    break
            if not subtask:
                raise ValueError(f"未找到子任务: {subtask_id}")

            valid_statuses = {"pending", "running", "completed", "failed"}
            if "status" in updates:
                status = updates["status"]
                if status not in valid_statuses:
                    raise ValueError(f"非法状态: {status}")
                subtask["status"] = status

            if "result" in updates:
                subtask["result"] = str(updates.get("result", "")).strip()

            subtask["updated_at"] = _now()
            task["updated_at"] = _now()
            self._save_locked()
            return copy.deepcopy(subtask)

    # ==================== 对话历史 ====================

    def add_conversation(self, task_id: str, speaker_id: str, message: str, subtask_id: str = "") -> None:
        with self._lock:
            task = None
            for t in self._state["tasks"]:
                if t["id"] == task_id:
                    task = t
                    break
            if not task:
                raise ValueError(f"未找到任务: {task_id}")

            entry = {
                "id": f"msg-{uuid.uuid4().hex[:8]}",
                "speaker_id": speaker_id,
                "message": message.strip(),
                "subtask_id": subtask_id,
                "created_at": _now(),
            }

            if subtask_id:
                for st in task["subtasks"]:
                    if st["id"] == subtask_id:
                        st["conversation"].append(entry)
                        break
            else:
                task["conversation"].append(entry)

            task["updated_at"] = _now()
            self._save_locked()

    # ==================== 事件 ====================

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            events = copy.deepcopy(self._state.get("recent_events", [])[:limit])
        return events

    # ==================== 老板要求 ====================

    def list_directives(self, active_only: bool = False) -> list[dict[str, Any]]:
        """列出老板要求，可选仅返回生效中的。"""
        with self._lock:
            directives = copy.deepcopy(self._state.get("boss_directives", []))
        if active_only:
            directives = [d for d in directives if d.get("active", True)]
        # 按创建时间倒序
        directives.sort(key=lambda x: x["created_at"], reverse=True)
        return directives

    def get_directive(self, directive_id: str) -> dict[str, Any] | None:
        """获取单条老板要求。"""
        with self._lock:
            for d in self._state.get("boss_directives", []):
                if d["id"] == directive_id:
                    return copy.deepcopy(d)
        return None

    def add_directive(self, content: str, category: str = "general") -> dict[str, Any]:
        """新增一条老板要求。"""
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("要求内容不能为空")

        with self._lock:
            directive = self._make_directive(clean_content, category)
            self._state.setdefault("boss_directives", []).append(directive)
            self._append_event("directive", f"老板新增要求：{clean_content[:60]}")
            self._save_locked()
            return copy.deepcopy(directive)

    def update_directive(self, directive_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """更新一条老板要求。"""
        with self._lock:
            directive = None
            for d in self._state.get("boss_directives", []):
                if d["id"] == directive_id:
                    directive = d
                    break
            if not directive:
                raise ValueError(f"未找到要求: {directive_id}")

            if "content" in updates:
                content = str(updates["content"] or "").strip()
                if not content:
                    raise ValueError("要求内容不能为空")
                directive["content"] = content

            if "category" in updates:
                directive["category"] = str(updates.get("category", "general")).strip() or "general"

            if "active" in updates:
                directive["active"] = bool(updates["active"])

            directive["updated_at"] = _now()
            self._append_event("directive", f"更新老板要求：{directive['content'][:60]}")
            self._save_locked()
            return copy.deepcopy(directive)

    def delete_directive(self, directive_id: str) -> None:
        """删除一条老板要求。"""
        with self._lock:
            for i, d in enumerate(self._state.get("boss_directives", [])):
                if d["id"] == directive_id:
                    removed = self._state["boss_directives"].pop(i)
                    self._append_event("directive", f"删除老板要求：{removed['content'][:60]}")
                    self._save_locked()
                    return
            raise ValueError(f"未找到要求: {directive_id}")

    def get_active_directives_text(self) -> str:
        """获取所有生效中的老板要求，格式化为文本（供 CTO 系统提示使用）。"""
        directives = self.list_directives(active_only=True)
        if not directives:
            return ""
        category_names = {
            "general": "通用",
            "quality": "质量要求",
            "style": "代码风格",
            "process": "流程规范",
            "tech": "技术偏好",
        }
        lines = []
        for d in directives:
            cat = category_names.get(d.get("category", "general"), d.get("category", "通用"))
            lines.append(f"- [{cat}] {d['content']}")
        return "\n".join(lines)

    # ==================== 权限审批 ====================

    def create_approval(self, worker_id: str, worker_name: str, task_id: str,
                        description: str, command_preview: str) -> dict[str, Any]:
        """创建权限审批请求，等待老板在 Web 页面确认。"""
        with self._lock:
            approval = self._make_approval(worker_id, worker_name, task_id, description, command_preview)
            self._state.setdefault("pending_approvals", []).append(approval)
            self._append_event("approval", f"员工 {worker_name} 请求执行权限：{description[:60]}", role_id=worker_id, task_id=task_id)
            self._save_locked()
            return copy.deepcopy(approval)

    def list_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        """列出审批请求，可按状态筛选。"""
        with self._lock:
            approvals = copy.deepcopy(self._state.get("pending_approvals", []))
        if status:
            approvals = [a for a in approvals if a["status"] == status]
        # 按创建时间倒序
        approvals.sort(key=lambda x: x["created_at"], reverse=True)
        return approvals

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        """获取单个审批请求。"""
        with self._lock:
            for a in self._state.get("pending_approvals", []):
                if a["id"] == approval_id:
                    return copy.deepcopy(a)
        return None

    def resolve_approval(self, approval_id: str, approved: bool) -> dict[str, Any]:
        """处理审批请求：approved=True 批准，False 拒绝。"""
        with self._lock:
            approval = None
            for a in self._state.get("pending_approvals", []):
                if a["id"] == approval_id:
                    approval = a
                    break
            if not approval:
                raise ValueError(f"未找到审批请求: {approval_id}")
            if approval["status"] != "pending":
                raise ValueError(f"审批已处理: {approval['status']}")

            approval["status"] = "approved" if approved else "rejected"
            approval["resolved_at"] = _now()

            action = "批准" if approved else "拒绝"
            self._append_event(
                "approval",
                f"老板{action}了 {approval['worker_name']} 的执行权限请求",
                role_id=approval["worker_id"],
                task_id=approval["task_id"],
            )
            self._save_locked()
            return copy.deepcopy(approval)
