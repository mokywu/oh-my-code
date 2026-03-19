import type { Task } from '../types';

interface Props {
  tasks: Task[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
}

const statusLabels: Record<string, string> = {
  pending: '待处理',
  analyzing: '分析中',
  assigned: '已分配',
  running: '进行中',
  completed: '已完成',
  cancelled: '已取消',
};

export default function TaskList({ tasks, selectedId, onSelect, onAdd }: Props) {
  return (
    <div className="card">
      <div className="list-header">
        <h2 className="section-title">📋 任务列表</h2>
        <button className="primary" onClick={onAdd}>+ 新建</button>
      </div>
      <div className="task-list">
        {tasks.length === 0 ? (
          <div className="empty-state">
            <p className="muted">暂无任务</p>
          </div>
        ) : (
          tasks.map(t => (
            <div
              key={t.id}
              className={`task-item ${selectedId === t.id ? 'selected' : ''}`}
              onClick={() => onSelect(t.id)}
            >
              <div className="task-item-header">
                <span className="task-title">{t.title}</span>
                <span className={`badge ${t.status}`}>{statusLabels[t.status]}</span>
              </div>
              <p className="task-desc muted small">
                {t.description || '无描述'}
              </p>
              <div className="task-meta">
                <span className="muted small">{t.subtasks.length} 子任务</span>
                <span className="muted small">{t.conversation.length} 条对话</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
