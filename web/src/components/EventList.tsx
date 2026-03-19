import type { Event } from '../types';

interface Props {
  events: Event[];
}

const kindIcons: Record<string, string> = {
  system: '⚙️',
  config: '🔧',
  task: '📋',
  focus: '🎯',
};

export default function EventList({ events }: Props) {
  return (
    <div className="card">
      <h2 className="section-title">📜 最近动态</h2>
      <div className="event-list">
        {events.length === 0 ? (
          <p className="muted">暂无动态</p>
        ) : (
          events.map((e, i) => (
            <div key={i} className="event-item">
              <div className="event-header">
                <span className="event-icon">{kindIcons[e.kind] || '📌'}</span>
                <span className="muted small">{e.created_at}</span>
              </div>
              <p className="event-message">{e.message}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
