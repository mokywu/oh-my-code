import type { Approval } from '../types';

interface Props {
  approvals: Approval[];
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
}

/** 格式化时间为相对时间 */
function timeAgo(isoStr: string): string {
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}秒前`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  return `${Math.floor(hours / 24)}天前`;
}

/** 权限审批列表组件 */
export default function ApprovalList({ approvals, onApprove, onReject }: Props) {
  const pending = approvals.filter(a => a.status === 'pending');
  const resolved = approvals.filter(a => a.status !== 'pending');

  return (
    <div className="card">
      <h2 className="section-title">🔐 权限审批</h2>

      {pending.length === 0 && resolved.length === 0 && (
        <div className="empty-state">
          <p className="muted">暂无审批请求</p>
          <p className="muted small" style={{ marginTop: 8 }}>
            当员工需要文件写入权限时，审批请求会出现在这里
          </p>
        </div>
      )}

      {pending.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, color: 'var(--warning)', marginBottom: 12 }}>
            ⏳ 待审批 ({pending.length})
          </h3>
          <div className="approval-list">
            {pending.map(a => (
              <div key={a.id} className="approval-item pending">
                <div className="approval-header">
                  <div>
                    <span className="worker-name">👨‍💻 {a.worker_name}</span>
                    <span className="muted small" style={{ marginLeft: 8 }}>{timeAgo(a.created_at)}</span>
                  </div>
                  <span className="badge running">待审批</span>
                </div>
                <div className="approval-desc">
                  <p style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 8 }}>{a.description}</p>
                  {a.command_preview && (
                    <div className="approval-cmd">
                      <code>{a.command_preview}</code>
                    </div>
                  )}
                  {a.task_id && (
                    <p className="muted small">关联任务: {a.task_id}</p>
                  )}
                </div>
                <div className="approval-actions">
                  <button className="primary" onClick={() => onApprove(a.id)}>
                    ✅ 批准执行
                  </button>
                  <button className="danger" onClick={() => onReject(a.id)}>
                    ❌ 拒绝
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {resolved.length > 0 && (
        <div>
          <h3 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12 }}>
            📋 历史记录 ({resolved.length})
          </h3>
          <div className="approval-list">
            {resolved.slice(0, 10).map(a => (
              <div key={a.id} className={`approval-item ${a.status}`}>
                <div className="approval-header">
                  <div>
                    <span className="worker-name">👨‍💻 {a.worker_name}</span>
                    <span className="muted small" style={{ marginLeft: 8 }}>{timeAgo(a.resolved_at || a.created_at)}</span>
                  </div>
                  <span className={`badge ${a.status === 'approved' ? 'completed' : 'failed'}`}>
                    {a.status === 'approved' ? '已批准' : '已拒绝'}
                  </span>
                </div>
                <p className="muted small" style={{ marginTop: 4 }}>
                  {a.description.slice(0, 80)}{a.description.length > 80 ? '...' : ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
