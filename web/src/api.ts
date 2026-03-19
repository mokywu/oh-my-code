import type { Role, Task, Snapshot, Subtask, Approval, Directive } from './types';

const API_BASE = '/api';

async function request<T>(path: string, method: string = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `请求失败: ${res.status}`);
  }
  return data;
}

// 快照
export const api = {
  getSnapshot: () => request<Snapshot>('/state'),

  // 角色
  listRoles: (type?: string) => request<Role[]>(type ? `/roles?type=${type}` : '/roles'),
  getRole: (id: string) => request<Role>(`/roles/${encodeURIComponent(id)}`),
  addWorker: (name: string) => request<Role>('/roles', 'POST', { name, type: 'worker' }),
  updateRole: (id: string, updates: Partial<Role>) => request<Role>(`/roles/${encodeURIComponent(id)}`, 'PUT', updates),
  deleteRole: (id: string) => request<void>(`/roles/${encodeURIComponent(id)}`, 'DELETE'),

  // 任务
  listTasks: (status?: string) => request<Task[]>(status ? `/tasks?status=${status}` : '/tasks'),
  getTask: (id: string) => request<Task>(`/tasks/${encodeURIComponent(id)}`),
  createTask: (title: string, description?: string) => request<Task>('/tasks', 'POST', { title, description }),
  updateTask: (id: string, updates: Partial<Task>) => request<Task>(`/tasks/${encodeURIComponent(id)}`, 'PUT', updates),
  deleteTask: (id: string) => request<void>(`/tasks/${encodeURIComponent(id)}`, 'DELETE'),

  // 子任务
  addSubtask: (taskId: string, workerId: string, content: string) =>
    request<Subtask>(`/tasks/${encodeURIComponent(taskId)}/subtasks`, 'POST', { worker_id: workerId, content }),
  updateSubtask: (taskId: string, subtaskId: string, updates: Partial<Subtask>) =>
    request<Subtask>(`/tasks/${encodeURIComponent(taskId)}/subtasks/${encodeURIComponent(subtaskId)}`, 'PUT', updates),

  // 事件
  getEvents: (limit?: number) => request<Event[]>(limit ? `/events?limit=${limit}` : '/events'),

  // 审批
  listApprovals: (status?: string) => request<Approval[]>(status ? `/approvals?status=${status}` : '/approvals'),
  approveApproval: (id: string) => request<Approval>(`/approvals/${encodeURIComponent(id)}/approve`, 'POST'),
  rejectApproval: (id: string) => request<Approval>(`/approvals/${encodeURIComponent(id)}/reject`, 'POST'),

  // 老板要求
  listDirectives: (activeOnly?: boolean) => request<Directive[]>(activeOnly ? '/directives?active=true' : '/directives'),
  addDirective: (content: string, category?: string) => request<Directive>('/directives', 'POST', { content, category }),
  updateDirective: (id: string, updates: Partial<Directive>) => request<Directive>(`/directives/${encodeURIComponent(id)}`, 'PUT', updates),
  deleteDirective: (id: string) => request<void>(`/directives/${encodeURIComponent(id)}`, 'DELETE'),
};
