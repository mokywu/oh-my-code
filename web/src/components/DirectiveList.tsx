import { useState } from 'react';
import type { Directive, DirectiveCategory } from '../types';

const CATEGORY_LABELS: Record<DirectiveCategory, string> = {
  general: '通用',
  quality: '质量要求',
  style: '代码风格',
  process: '流程规范',
  tech: '技术偏好',
};

const CATEGORY_ICONS: Record<DirectiveCategory, string> = {
  general: '📋',
  quality: '✅',
  style: '🎨',
  process: '📐',
  tech: '⚙️',
};

interface Props {
  directives: Directive[];
  onAdd: (content: string, category: DirectiveCategory) => Promise<void>;
  onUpdate: (id: string, updates: Partial<Directive>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export default function DirectiveList({ directives, onAdd, onUpdate, onDelete }: Props) {
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState<DirectiveCategory>('general');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [editCategory, setEditCategory] = useState<DirectiveCategory>('general');
  const [adding, setAdding] = useState(false);

  /** 提交新增要求 */
  const handleAdd = async () => {
    const trimmed = newContent.trim();
    if (!trimmed) return;
    setAdding(true);
    try {
      await onAdd(trimmed, newCategory);
      setNewContent('');
      setNewCategory('general');
    } finally {
      setAdding(false);
    }
  };

  /** 进入编辑模式 */
  const startEdit = (d: Directive) => {
    setEditingId(d.id);
    setEditContent(d.content);
    setEditCategory(d.category);
  };

  /** 保存编辑 */
  const handleSaveEdit = async (id: string) => {
    const trimmed = editContent.trim();
    if (!trimmed) return;
    await onUpdate(id, { content: trimmed, category: editCategory });
    setEditingId(null);
  };

  const activeDirectives = directives.filter(d => d.active);
  const inactiveDirectives = directives.filter(d => !d.active);

  return (
    <div className="card">
      <h2 className="section-title">📌 老板要求</h2>
      <p className="muted" style={{ marginBottom: 16, fontSize: 13 }}>
        在此记录你的偏好和要求，CTO 制定方案时会自动参考这些要求。
      </p>

      {/* 新增表单 */}
      <div className="directive-add-form">
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <textarea
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            placeholder="输入你的要求，例如：代码必须有完善的注释、优先使用 TypeScript、每次修改都要跑测试..."
            rows={2}
            style={{ flex: 1, minHeight: 60 }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAdd();
              }
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 8 }}>
          <select
            value={newCategory}
            onChange={e => setNewCategory(e.target.value as DirectiveCategory)}
            style={{ width: 140 }}
          >
            {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{CATEGORY_ICONS[key as DirectiveCategory]} {label}</option>
            ))}
          </select>
          <button
            className="primary"
            onClick={handleAdd}
            disabled={!newContent.trim() || adding}
            style={{ marginLeft: 'auto' }}
          >
            {adding ? '添加中...' : '+ 添加要求'}
          </button>
        </div>
      </div>

      {/* 生效中的要求 */}
      {activeDirectives.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: 14, color: 'var(--success)', marginBottom: 10 }}>
            ✅ 生效中 ({activeDirectives.length})
          </h3>
          <div className="directive-list">
            {activeDirectives.map(d => (
              <div key={d.id} className="directive-item active">
                {editingId === d.id ? (
                  <div className="directive-edit">
                    <textarea
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      rows={2}
                    />
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                      <select
                        value={editCategory}
                        onChange={e => setEditCategory(e.target.value as DirectiveCategory)}
                        style={{ width: 140 }}
                      >
                        {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                          <option key={key} value={key}>{label}</option>
                        ))}
                      </select>
                      <button className="primary" onClick={() => handleSaveEdit(d.id)}>保存</button>
                      <button onClick={() => setEditingId(null)}>取消</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="directive-header">
                      <span className="directive-category">
                        {CATEGORY_ICONS[d.category]} {CATEGORY_LABELS[d.category]}
                      </span>
                      <span className="muted small">{new Date(d.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="directive-content">{d.content}</div>
                    <div className="directive-actions">
                      <button onClick={() => startEdit(d)}>编辑</button>
                      <button onClick={() => onUpdate(d.id, { active: false })}>暂停</button>
                      <button className="danger" onClick={() => {
                        if (confirm('确认删除此要求？')) onDelete(d.id);
                      }}>删除</button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 已暂停的要求 */}
      {inactiveDirectives.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 10 }}>
            ⏸️ 已暂停 ({inactiveDirectives.length})
          </h3>
          <div className="directive-list">
            {inactiveDirectives.map(d => (
              <div key={d.id} className="directive-item inactive">
                <div className="directive-header">
                  <span className="directive-category muted">
                    {CATEGORY_ICONS[d.category]} {CATEGORY_LABELS[d.category]}
                  </span>
                  <span className="muted small">{new Date(d.created_at).toLocaleDateString()}</span>
                </div>
                <div className="directive-content muted">{d.content}</div>
                <div className="directive-actions">
                  <button className="primary" onClick={() => onUpdate(d.id, { active: true })}>启用</button>
                  <button className="danger" onClick={() => {
                    if (confirm('确认删除此要求？')) onDelete(d.id);
                  }}>删除</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 空状态 */}
      {directives.length === 0 && (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <p className="muted">还没有添加任何要求</p>
          <p className="muted small">添加你的偏好和要求，CTO 在制定方案时会自动参考</p>
        </div>
      )}
    </div>
  );
}
