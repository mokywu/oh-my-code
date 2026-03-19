export type RoleType = 'boss' | 'cto' | 'worker';
export type TaskStatus = 'pending' | 'analyzing' | 'assigned' | 'running' | 'completed' | 'cancelled' | 'pending_confirmation';
export type SubtaskStatus = 'pending' | 'running' | 'completed' | 'failed';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface Role {
  id: string;
  type: RoleType;
  name: string;
  project_path: string;
  rules: string[];
  context: string;
  api_key: string;
  system_prompt: string;
  model: string;
  use_claude_cli?: boolean;
  created_at: string;
  updated_at: string;
  path_exists?: boolean;
  effective_path?: string;
}

export interface Subtask {
  id: string;
  task_id: string;
  worker_id: string;
  content: string;
  status: SubtaskStatus;
  result: string;
  conversation: ConversationEntry[];
  created_at: string;
  updated_at: string;
}

export interface ConversationEntry {
  id: string;
  speaker_id: string;
  message: string;
  subtask_id: string;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  creator_id: string;
  boss_id: string;
  subtasks: Subtask[];
  conversation: ConversationEntry[];
  created_at: string;
  updated_at: string;
}

export interface Event {
  kind: string;
  message: string;
  role_id: string;
  task_id: string;
  created_at: string;
}

export interface Approval {
  id: string;
  worker_id: string;
  worker_name: string;
  task_id: string;
  description: string;
  command_preview: string;
  status: ApprovalStatus;
  created_at: string;
  resolved_at: string;
}

export type DirectiveCategory = 'general' | 'quality' | 'style' | 'process' | 'tech';

export interface Directive {
  id: string;
  content: string;
  category: DirectiveCategory;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Stats {
  worker_count: number;
  task_count: number;
  pending_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  pending_approvals: number;
  directive_count: number;
}

export interface Snapshot {
  version: number;
  root_dir: string;
  state_file: string;
  roles: Role[];
  tasks: Task[];
  recent_events: Event[];
  pending_approvals: Approval[];
  boss_directives: Directive[];
  stats: Stats;
  generated_at: string;
}
