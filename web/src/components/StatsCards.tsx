import type { Stats } from '../types';

interface Props {
  stats?: Stats;
}

export default function StatsCards({ stats }: Props) {
  const cards = [
    { label: '员工数', value: stats?.worker_count || 0, color: 'var(--accent)' },
    { label: '总任务', value: stats?.task_count || 0, color: 'var(--purple)' },
    { label: '进行中', value: stats?.running_tasks || 0, color: 'var(--warning)' },
    { label: '已完成', value: stats?.completed_tasks || 0, color: 'var(--success)' },
  ];

  return (
    <div className="stats-grid">
      {cards.map(c => (
        <div key={c.label} className="stat-card">
          <div className="stat-label">{c.label}</div>
          <div className="stat-value" style={{ color: c.color }}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}
