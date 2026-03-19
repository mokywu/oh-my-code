import type { Role } from '../types';

interface Props {
  workers: Role[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
}

export default function RoleList({ workers, selectedId, onSelect, onAdd }: Props) {
  return (
    <div className="card">
      <div className="list-header">
        <h2 className="section-title">👨‍💻 员工列表</h2>
        <button className="primary" onClick={onAdd}>+ 新增</button>
      </div>
      <div className="role-list">
        {workers.length === 0 ? (
          <div className="empty-state">
            <p className="muted">暂无员工，点击新增添加</p>
          </div>
        ) : (
          workers.map(w => (
            <div
              key={w.id}
              className={`role-item ${selectedId === w.id ? 'selected' : ''}`}
              onClick={() => onSelect(w.id)}
            >
              <div className="role-item-header">
                <span className="role-name">{w.name}</span>
                <span className={`badge ${w.path_exists ? 'completed' : 'pending'}`}>
                  {w.path_exists ? '路径正常' : '路径异常'}
                </span>
              </div>
              <p className="role-path muted small">
                {w.project_path || '未配置项目路径'}
              </p>
              <div className="role-meta">
                <span className="muted small">{w.rules.length} 规则</span>
                <span className="muted small">{w.context ? '有上下文' : '无上下文'}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
