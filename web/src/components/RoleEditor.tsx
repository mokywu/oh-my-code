import { useState } from 'react';
import type { Role } from '../types';

interface Props {
  role: Role;
  onSave: (updates: Partial<Role>) => Promise<void>;
  onDelete: () => Promise<void>;
}

export default function RoleEditor({ role, onSave, onDelete }: Props) {
  const [form, setForm] = useState({
    name: role.name,
    project_path: role.project_path,
    rules: role.rules.join('\n'),
    context: role.context,
    api_key: role.api_key,
    system_prompt: role.system_prompt,
    model: role.model,
    use_claude_cli: role.use_claude_cli || false,
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await onSave({
        ...form,
        rules: form.rules.split('\n').filter(Boolean),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <h2 className="section-title">✏️ 编辑员工</h2>

      <div className="form-grid">
        <div className="field">
          <label>员工名称</label>
          <input
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
          />
        </div>

        <div className="field">
          <label>项目本地路径</label>
          <input
            value={form.project_path}
            onChange={e => setForm({ ...form, project_path: e.target.value })}
            placeholder="例如 D:/work/my-project"
          />
          {form.project_path && (
            <p className={`small ${role.path_exists ? 'success' : 'danger'}`}>
              {role.path_exists ? '✓ 路径存在' : '✗ 路径不存在'}
            </p>
          )}
        </div>

        <div className="field">
          <label>AI 模型</label>
          <input
            value={form.model}
            onChange={e => setForm({ ...form, model: e.target.value })}
            placeholder="例如 claude-3-5-sonnet-20241022"
          />
        </div>

        <div className="field">
          <label>API Key</label>
          <input
            type="password"
            value={form.api_key}
            onChange={e => setForm({ ...form, api_key: e.target.value })}
            placeholder="sk-..."
          />
        </div>

        <div className="field">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.use_claude_cli}
              onChange={e => setForm({ ...form, use_claude_cli: e.target.checked })}
            />
            <span>使用 Claude CLI 执行任务</span>
          </label>
          <p className="small muted">
            启用后，员工将直接调用 claude 命令在项目目录执行任务
          </p>
        </div>

        <div className="field">
          <label>部门 Rules（每行一条）</label>
          <textarea
            value={form.rules}
            onChange={e => setForm({ ...form, rules: e.target.value })}
            placeholder="例如：&#10;修改代码前先读取 README&#10;只能在当前项目目录内工作"
            rows={4}
          />
        </div>

        <div className="field">
          <label>部门上下文</label>
          <textarea
            value={form.context}
            onChange={e => setForm({ ...form, context: e.target.value })}
            placeholder="技术栈、模块边界、交付要求等长期上下文"
            rows={4}
          />
        </div>

        <div className="field">
          <label>自定义 System Prompt</label>
          <textarea
            value={form.system_prompt}
            onChange={e => setForm({ ...form, system_prompt: e.target.value })}
            placeholder="留空则使用默认 prompt"
            rows={3}
          />
        </div>
      </div>

      <div className="form-meta muted small">
        <div>ID: {role.id}</div>
        <div>创建: {role.created_at}</div>
        <div>更新: {role.updated_at}</div>
      </div>

      <div className="form-actions">
        <button className="primary" onClick={handleSubmit} disabled={saving}>
          {saving ? '保存中...' : '保存配置'}
        </button>
        <button className="danger" onClick={onDelete}>删除员工</button>
      </div>
    </div>
  );
}
