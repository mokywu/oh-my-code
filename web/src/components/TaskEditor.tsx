import { useState } from 'react';
import type { Task, Role, Subtask } from '../types';

interface Props {
  task: Task;
  workers: Role[];
  onSave: (updates: Partial<Task>) => Promise<void>;
  onDelete: () => Promise<void>;
  onAddSubtask: (workerId: string, content: string) => Promise<void>;
}

const statusLabels: Record<string, string> = {
  pending: '待处理',
  analyzing: '分析中',
  assigned: '已分配',
  running: '进行中',
  completed: '已完成',
  cancelled: '已取消',
};

const subtaskStatusLabels: Record<string, string> = {
  pending: '待处理',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
};

export default function TaskEditor({ task, workers, onSave, onDelete, onAddSubtask }: Props) {
  const [form, setForm] = useState({
    title: task.title,
    description: task.description,
    status: task.status,
  });
  const [saving, setSaving] = useState(false);
  const [showAddSubtask, setShowAddSubtask] = useState(false);
  const [newSubtask, setNewSubtask] = useState({ workerId: '', content: '' });

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  const handleAddSubtask = async () => {
    if (!newSubtask.workerId || !newSubtask.content) return;
    await onAddSubtask(newSubtask.workerId, newSubtask.content);
    setNewSubtask({ workerId: '', content: '' });
    setShowAddSubtask(false);
  };

  const getWorkerName = (id: string) => workers.find(w => w.id === id)?.name || id;

  return (
    <div className="card">
      <h2 className="section-title">📝 任务详情</h2>

      <div className="form-grid">
        <div className="field">
          <label>任务标题</label>
          <input
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
          />
        </div>

        <div className="field">
          <label>任务描述</label>
          <textarea
            value={form.description}
            onChange={e => setForm({ ...form, description: e.target.value })}
            placeholder="详细描述任务目标..."
            rows={3}
          />
        </div>

        <div className="field">
          <label>状态</label>
          <select
            value={form.status}
            onChange={e => setForm({ ...form, status: e.target.value as Task['status'] })}
          >
            {Object.entries(statusLabels).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-actions">
        <button className="primary" onClick={handleSubmit} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </button>
        <button className="danger" onClick={onDelete}>删除任务</button>
      </div>

      {/* 子任务 */}
      <div className="subtasks-section">
        <div className="list-header">
          <h3 className="section-title">📦 子任务 ({task.subtasks.length})</h3>
          <button onClick={() => setShowAddSubtask(!showAddSubtask)}>
            {showAddSubtask ? '取消' : '+ 分配'}
          </button>
        </div>

        {showAddSubtask && (
          <div className="add-subtask-form">
            <select
              value={newSubtask.workerId}
              onChange={e => setNewSubtask({ ...newSubtask, workerId: e.target.value })}
            >
              <option value="">选择员工...</option>
              {workers.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <textarea
              value={newSubtask.content}
              onChange={e => setNewSubtask({ ...newSubtask, content: e.target.value })}
              placeholder="任务内容..."
              rows={2}
            />
            <button className="primary" onClick={handleAddSubtask}>确认分配</button>
          </div>
        )}

        <div className="subtask-list">
          {task.subtasks.length === 0 ? (
            <p className="muted small">暂无子任务</p>
          ) : (
            task.subtasks.map(st => (
              <div key={st.id} className="subtask-item">
                <div className="subtask-header">
                  <span className="worker-name">{getWorkerName(st.worker_id)}</span>
                  <span className={`badge ${st.status}`}>{subtaskStatusLabels[st.status]}</span>
                </div>
                <p className="subtask-content">{st.content}</p>
                {st.result && <p className="subtask-result muted small">结果: {st.result}</p>}
              </div>
            ))
          )}
        </div>
      </div>

      {/* 对话历史 */}
      {task.conversation.length > 0 && (
        <div className="conversation-section">
          <h3 className="section-title">💬 对话历史 ({task.conversation.length})</h3>
          <div className="conversation-list">
            {task.conversation.slice(-10).map(msg => (
              <div key={msg.id} className="msg-item">
                <div className="msg-header">
                  <span className="msg-speaker">{getWorkerName(msg.speaker_id)}</span>
                  <span className="muted small">{msg.created_at}</span>
                </div>
                <p className="msg-text">{msg.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="form-meta muted small">
        <div>ID: {task.id}</div>
        <div>创建: {task.created_at}</div>
        <div>更新: {task.updated_at}</div>
      </div>
    </div>
  );
}
