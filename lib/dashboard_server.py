"""本地 Dashboard 服务：提供 REST API 供 React 前端访问。"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class LocalDashboardServer:
    """启动本地 HTTP 服务，提供 REST API。"""

    def __init__(self, state, host: str = "127.0.0.1", port: int = 8765):
        self._state = state
        self._host = host
        self._preferred_port = port
        self._httpd = None
        self._thread = None
        self.url = ""

    def _make_handler(self):
        state = self._state

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, payload, status=200):
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def _read_json(self):
                content_length = int(self.headers.get("Content-Length", "0") or "0")
                if content_length <= 0:
                    return {}
                raw = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw) if raw else {}

            def _send_error(self, message: str, status: int = 400):
                self._send_json({"error": message}, status)

            def _get_path_id(self, prefix: str) -> str | None:
                parsed = urlparse(self.path)
                if parsed.path.startswith(prefix):
                    return parsed.path[len(prefix):]
                return None

            def _get_query_param(self, name: str) -> str | None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                values = params.get(name, [])
                return values[0] if values else None

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            # ==================== API 路由 ====================

            def do_GET(self):
                parsed = urlparse(self.path)

                try:
                    # 快照
                    if parsed.path == "/api/state":
                        self._send_json(state.get_snapshot())
                        return

                    # 角色列表
                    if parsed.path == "/api/roles":
                        role_type = self._get_query_param("type")
                        self._send_json(state.list_roles(role_type))
                        return

                    # 单个角色
                    role_id = self._get_path_id("/api/roles/")
                    if role_id:
                        role = state.get_role(role_id)
                        if role:
                            self._send_json(role)
                        else:
                            self._send_error("未找到角色", 404)
                        return

                    # 任务列表
                    if parsed.path == "/api/tasks":
                        task_status = self._get_query_param("status")
                        self._send_json(state.list_tasks(task_status))
                        return

                    # 单个任务
                    task_id = self._get_path_id("/api/tasks/")
                    if task_id and "/" not in task_id:
                        task = state.get_task(task_id)
                        if task:
                            self._send_json(task)
                        else:
                            self._send_error("未找到任务", 404)
                        return

                    # 事件列表
                    if parsed.path == "/api/events":
                        limit_str = self._get_query_param("limit")
                        limit = int(limit_str) if limit_str else 50
                        self._send_json(state.get_recent_events(limit))
                        return

                    # 审批列表
                    if parsed.path == "/api/approvals":
                        status_filter = self._get_query_param("status")
                        self._send_json(state.list_approvals(status_filter))
                        return

                    # 单个审批
                    approval_id = self._get_path_id("/api/approvals/")
                    if approval_id and "/" not in approval_id:
                        approval = state.get_approval(approval_id)
                        if approval:
                            self._send_json(approval)
                        else:
                            self._send_error("未找到审批请求", 404)
                        return

                    # 老板要求列表
                    if parsed.path == "/api/directives":
                        active_only = self._get_query_param("active") == "true"
                        self._send_json(state.list_directives(active_only))
                        return

                    # 单条老板要求
                    directive_id = self._get_path_id("/api/directives/")
                    if directive_id and "/" not in directive_id:
                        directive = state.get_directive(directive_id)
                        if directive:
                            self._send_json(directive)
                        else:
                            self._send_error("未找到该要求", 404)
                        return

                    self._send_error("Not found", 404)

                except Exception as e:
                    self._send_error(str(e), 500)

            def do_POST(self):
                parsed = urlparse(self.path)

                try:
                    # 新增员工
                    if parsed.path == "/api/roles":
                        payload = self._read_json()
                        name = payload.get("name", "")
                        if not name:
                            self._send_error("名称不能为空")
                            return
                        role = state.add_worker(name)
                        self._send_json(role, 201)
                        return

                    # 新增任务
                    if parsed.path == "/api/tasks":
                        payload = self._read_json()
                        title = payload.get("title", "")
                        if not title:
                            self._send_error("标题不能为空")
                            return
                        task = state.create_task(title, payload.get("description", ""))
                        self._send_json(task, 201)
                        return

                    # 新增子任务
                    task_id = self._get_path_id("/api/tasks/")
                    if task_id and parsed.path.endswith("/subtasks"):
                        payload = self._read_json()
                        worker_id = payload.get("worker_id", "")
                        content = payload.get("content", "")
                        if not worker_id or not content:
                            self._send_error("缺少 worker_id 或 content")
                            return
                        subtask = state.add_subtask(task_id, worker_id, content)
                        self._send_json(subtask, 201)
                        return

                    # 新增老板要求
                    if parsed.path == "/api/directives":
                        payload = self._read_json()
                        content = payload.get("content", "")
                        if not content:
                            self._send_error("要求内容不能为空")
                            return
                        category = payload.get("category", "general")
                        directive = state.add_directive(content, category)
                        self._send_json(directive, 201)
                        return

                    # 审批操作：批准
                    approval_id = self._get_path_id("/api/approvals/")
                    if approval_id:
                        if parsed.path.endswith("/approve"):
                            aid = approval_id.replace("/approve", "")
                            try:
                                result = state.resolve_approval(aid, approved=True)
                                self._send_json(result)
                            except ValueError as e:
                                self._send_error(str(e), 400)
                            return
                        elif parsed.path.endswith("/reject"):
                            aid = approval_id.replace("/reject", "")
                            try:
                                result = state.resolve_approval(aid, approved=False)
                                self._send_json(result)
                            except ValueError as e:
                                self._send_error(str(e), 400)
                            return

                    self._send_error("Not found", 404)

                except ValueError as e:
                    self._send_error(str(e), 400)
                except Exception as e:
                    self._send_error(str(e), 500)

            def do_PUT(self):
                parsed = urlparse(self.path)

                try:
                    # 更新角色
                    role_id = self._get_path_id("/api/roles/")
                    if role_id:
                        payload = self._read_json()
                        role = state.update_role(role_id, payload)
                        self._send_json(role)
                        return

                    # 更新任务
                    task_id = self._get_path_id("/api/tasks/")
                    if task_id and "/subtasks/" not in parsed.path:
                        payload = self._read_json()
                        task = state.update_task(task_id, payload)
                        self._send_json(task)
                        return

                    # 更新子任务
                    if "/subtasks/" in parsed.path:
                        parts = parsed.path.split("/")
                        if len(parts) >= 6:
                            task_id = parts[3]
                            subtask_id = parts[5]
                            payload = self._read_json()
                            subtask = state.update_subtask(task_id, subtask_id, payload)
                            self._send_json(subtask)
                            return

                    # 更新老板要求
                    directive_id = self._get_path_id("/api/directives/")
                    if directive_id:
                        payload = self._read_json()
                        directive = state.update_directive(directive_id, payload)
                        self._send_json(directive)
                        return

                    self._send_error("Not found", 404)

                except ValueError as e:
                    self._send_error(str(e), 400)
                except Exception as e:
                    self._send_error(str(e), 500)

            def do_DELETE(self):
                parsed = urlparse(self.path)

                try:
                    # 删除角色
                    role_id = self._get_path_id("/api/roles/")
                    if role_id:
                        state.delete_role(role_id)
                        self._send_json({"ok": True})
                        return

                    # 删除任务
                    task_id = self._get_path_id("/api/tasks/")
                    if task_id and "/subtasks/" not in parsed.path:
                        state.delete_task(task_id)
                        self._send_json({"ok": True})
                        return

                    # 删除老板要求
                    directive_id = self._get_path_id("/api/directives/")
                    if directive_id:
                        state.delete_directive(directive_id)
                        self._send_json({"ok": True})
                        return

                    self._send_error("Not found", 404)

                except ValueError as e:
                    self._send_error(str(e), 400)
                except Exception as e:
                    self._send_error(str(e), 500)

            def log_message(self, *_args):
                return

        return Handler

    def start(self) -> str:
        if self._httpd:
            return self.url

        handler = self._make_handler()
        last_error = None
        for port in range(self._preferred_port, self._preferred_port + 20):
            try:
                self._httpd = ThreadingHTTPServer((self._host, port), handler)
                self.url = f"http://{self._host}:{port}"
                break
            except OSError as error:
                last_error = error
                continue

        if not self._httpd:
            raise RuntimeError(f"启动 Dashboard 失败: {last_error}")

        import threading
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.url

    def stop(self) -> None:
        if not self._httpd:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
