import { useEffect, useState, useCallback } from 'react';
import { api } from './api';
import type { Snapshot, Role, Task, Event } from './types';
import RoleList from './components/RoleList';
import RoleEditor from './components/RoleEditor';
import TaskList from './components/TaskList';
import TaskEditor from './components/TaskEditor';
import EventList from './components/EventList';
import StatsCards from './components/StatsCards';
import ApprovalList from './components/ApprovalList';
import DirectiveList from './components/DirectiveList';

type Tab = 'overview' | 'workers' | 'tasks' | 'approvals' | 'directives';

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const loadSnapshot = useCallback(async () => {
    try {
      const data = await api.getSnapshot();
      setSnapshot(data);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSnapshot();
    const timer = setInterval(loadSnapshot, 3000);
    return () => clearInterval(timer);
  }, [loadSnapshot]);

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  if (error) {
    return (
      <div className="error-page">
        <p className="danger">错误: {error}</p>
        <button onClick={loadSnapshot}>重试</button>
      </div>
    );
  }

  const boss = snapshot?.roles.find(r => r.type === 'boss');
  const cto = snapshot?.roles.find(r => r.type === 'cto');
  const workers = snapshot?.roles.filter(r => r.type === 'worker') || [];
  const pendingApprovals = snapshot?.stats?.pending_approvals || 0;

  const selectedRole = selectedRoleId ? snapshot?.roles.find(r => r.id === selectedRoleId) : null;
  const selectedTask = selectedTaskId ? snapshot?.tasks.find(t => t.id === selectedTaskId) : null;

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>oh-my-code 工作台</h1>
          <p className="muted">老板 → CTO → 员工 | 协作式 AI 开发团队</p>
        </div>
        <div className="header-right">
          <div className="org-info">
            <span className="badge completed">{boss?.name || '老板'}</span>
            <span className="arrow">→</span>
            <span className="badge running">{cto?.name || 'CTO'}</span>
            <span className="arrow">→</span>
            <span className="badge pending">{workers.length} 员工</span>
          </div>
        </div>
      </header>

      <nav className="tabs">
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>
          总览
        </button>
        <button className={tab === 'workers' ? 'active' : ''} onClick={() => setTab('workers')}>
          员工管理 ({workers.length})
        </button>
        <button className={tab === 'tasks' ? 'active' : ''} onClick={() => setTab('tasks')}>
          任务列表 ({snapshot?.stats.task_count || 0})
        </button>
        <button
          className={`${tab === 'approvals' ? 'active' : ''} ${pendingApprovals > 0 ? 'has-notification' : ''}`}
          onClick={() => setTab('approvals')}
        >
          🔐 权限审批
          {pendingApprovals > 0 && <span className="notification-badge">{pendingApprovals}</span>}
        </button>
        <button className={tab === 'directives' ? 'active' : ''} onClick={() => setTab('directives')}>
          📌 老板要求 ({snapshot?.stats.directive_count || 0})
        </button>
      </nav>

      <main className="main">
        {tab === 'overview' && (
          <div className="overview-layout">
            <div className="left-panel">
              <StatsCards stats={snapshot?.stats} />
              {pendingApprovals > 0 && (
                <div className="approval-banner" onClick={() => setTab('approvals')}>
                  <span>🔔</span>
                  <span>有 {pendingApprovals} 个权限请求等待审批</span>
                  <button className="primary" style={{ marginLeft: 'auto', padding: '6px 14px', fontSize: 13 }}>
                    去审批 →
                  </button>
                </div>
              )}
              <div className="card" style={{ marginTop: 16 }}>
                <h2 className="section-title">👥 组织架构</h2>
                <div className="org-tree">
                  <div className="org-node boss">
                    <div className="node-header">
                      <span className="role-icon">👔</span>
                      <span className="role-name">{boss?.name || '老板'}</span>
                    </div>
                    <p className="muted small">下达指令，确认完成</p>
                  </div>
                  <div className="org-node cto">
                    <div className="node-header">
                      <span className="role-icon">🧠</span>
                      <span className="role-name">{cto?.name || 'CTO'}</span>
                    </div>
                    <p className="muted small">拆解任务，分配协调</p>
                  </div>
                  <div className="workers-grid">
                    {workers.map(w => (
                      <div key={w.id} className="org-node worker" onClick={() => { setTab('workers'); setSelectedRoleId(w.id); }}>
                        <div className="node-header">
                          <span className="role-icon">👨‍💻</span>
                          <span className="role-name">{w.name}</span>
                        </div>
                        <p className="muted small">{w.project_path || '未配置路径'}</p>
                      </div>
                    ))}
                    <div className="org-node worker add" onClick={() => setTab('workers')}>
                      <span>+ 添加员工</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="right-panel">
              <EventList events={snapshot?.recent_events.slice(0, 20) || []} />
            </div>
          </div>
        )}

        {tab === 'workers' && (
          <div className="edit-layout">
            <div className="left-panel">
              <RoleList
                workers={workers}
                selectedId={selectedRoleId}
                onSelect={setSelectedRoleId}
                onAdd={async () => {
                  const name = prompt('请输入员工名称');
                  if (name) {
                    await api.addWorker(name);
                    loadSnapshot();
                  }
                }}
              />
            </div>
            <div className="right-panel">
              {selectedRole ? (
                <RoleEditor
                  role={selectedRole}
                  onSave={async (updates) => {
                    await api.updateRole(selectedRole.id, updates);
                    loadSnapshot();
                  }}
                  onDelete={async () => {
                    if (confirm(`确认删除员工【${selectedRole.name}】？`)) {
                      await api.deleteRole(selectedRole.id);
                      setSelectedRoleId(null);
                      loadSnapshot();
                    }
                  }}
                />
              ) : (
                <div className="card empty-state">
                  <p className="muted">选择一个员工进行编辑</p>
                </div>
              )}
            </div>
          </div>
        )}

        {tab === 'tasks' && (
          <div className="edit-layout">
            <div className="left-panel">
              <TaskList
                tasks={snapshot?.tasks || []}
                selectedId={selectedTaskId}
                onSelect={setSelectedTaskId}
                onAdd={async () => {
                  const title = prompt('请输入任务标题');
                  if (title) {
                    await api.createTask(title);
                    loadSnapshot();
                  }
                }}
              />
            </div>
            <div className="right-panel">
              {selectedTask ? (
                <TaskEditor
                  task={selectedTask}
                  workers={workers}
                  onSave={async (updates) => {
                    await api.updateTask(selectedTask.id, updates);
                    loadSnapshot();
                  }}
                  onDelete={async () => {
                    if (confirm(`确认删除任务【${selectedTask.title}】？`)) {
                      await api.deleteTask(selectedTask.id);
                      setSelectedTaskId(null);
                      loadSnapshot();
                    }
                  }}
                  onAddSubtask={async (workerId, content) => {
                    await api.addSubtask(selectedTask.id, workerId, content);
                    loadSnapshot();
                  }}
                />
              ) : (
                <div className="card empty-state">
                  <p className="muted">选择一个任务进行查看</p>
                </div>
              )}
            </div>
          </div>
        )}

        {tab === 'approvals' && (
          <ApprovalList
            approvals={snapshot?.pending_approvals || []}
            onApprove={async (id) => {
              await api.approveApproval(id);
              loadSnapshot();
            }}
            onReject={async (id) => {
              await api.rejectApproval(id);
              loadSnapshot();
            }}
          />
        )}

        {tab === 'directives' && (
          <DirectiveList
            directives={snapshot?.boss_directives || []}
            onAdd={async (content, category) => {
              await api.addDirective(content, category);
              loadSnapshot();
            }}
            onUpdate={async (id, updates) => {
              await api.updateDirective(id, updates);
              loadSnapshot();
            }}
            onDelete={async (id) => {
              await api.deleteDirective(id);
              loadSnapshot();
            }}
          />
        )}
      </main>
    </div>
  );
}
