export type StageStatus = 'started' | 'success' | 'failed' | 'repairing' | 'complete';

export type FailureClass =
  | 'semantic_drift'
  | 'contradiction_mismatch'
  | 'hook_redundancy'
  | 'explanatory_drift'
  | 'mechanism_mismatch'
  | 'identity_missing'
  | 'sales_drift'
  | 'length_violation'
  | 'format_error'
  | 'unknown';

export interface AttemptHistoryEntry {
  attempt: number;
  valid: boolean;
  scores: Record<string, number> | null;
  failure_class: string | null;
}

export interface StageTrace {
  stage: string;
  status: StageStatus;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  cost: number;
  output?: any;
  failure_class?: FailureClass | null;
  failure_reason: string;
  retry_count: number;
  validation_scores: Record<string, number>;
  attempts_history: AttemptHistoryEntry[];
}

export interface PipelineTrace {
  request_id: string;
  problem_id: string;
  context_id: number;
  stages: StageTrace[];
  total_latency_ms: number;
  total_cost: number;
  total_tokens_in: number;
  total_tokens_out: number;
  final_status: string;
}

export interface PipelineResult {
  final_email_id: number;
  subject_line: string;
  email: string;
  validation_scores: ValidationScores;
  attempts: AttemptCounts;
  trace?: PipelineTrace;
}

export interface FailureModeEntry {
  class: FailureClass;
  count: number;
  percentage: number;
}

export interface AnalyticsData {
  average_retries: number;
  top_failure_modes: FailureModeEntry[];
  validator_disagreement_rate: number;
  repair_success_rate: number;
  average_latency_ms: number;
  average_cost: number;
  total_emails_generated: number;
}

// ─── Per-context email analytics from backend ───
export interface StageAnalytics {
  id: number;
  score: number;
}

export interface AttemptHistoryItem {
  stage_name: string;
  attempt_number: number;
  status: string;
  failure_reason: string | null;
  failure_mode: string | null;
  latency: number;
  cost: number;
  input_tokens: number;
  output_tokens: number;
  model_name: string;
  output_text: string;
}

export interface EmailAnalytics {
  context_id: string;
  email_id: number;
  final_email: string;
  totals: {
    total_latency: number;
    total_cost: number;
    total_input_tokens: number;
    total_output_tokens: number;
    overall_score: number;
  };
  stages: Record<string, StageAnalytics>;
  attempt_history: AttemptHistoryItem[];
}

// ─── Backend Problem (GET /problems/{id}) ───
export interface Problem {
  id: string | number;
  problem_name: string;
  core_problem: string;
  system: string;
  causal_mechanism: string;
  failure_mode_A: string;
  failure_mode_B: string;
  failure_mode_A_mechanism: string;
  failure_mode_B_mechanism: string;
  contradiction: string;
  business_impact: string;
  solution_mechanism: string;
  solution_actor: string;
  created_at?: string;
  // Frontend-only fields (added after creation)
  problem_id?: string | number;
  snapshot?: ProblemSnapshot;
  fullData?: CreateProblemRequest;
  createdAt?: string;
}

// ─── Backend Context (GET /contexts/{id}) ───
export interface Context {
  id: string | number;
  problem_id: string | number;
  request_id?: string;
  industry: string;
  company_size: string;
  decision_actor: string;
  extra: string;
  constraints: string[];
  created_at?: string;
  // Frontend-only fields
  context_id?: string | number;
  snapshot?: ContextSnapshot;
  createdAt?: string;
}

// ─── Frontend-only types (localStorage cache) ───
export interface ProblemSnapshot {
  problem_name: string;
  system: string;
}

export interface ContextSnapshot {
  industry: string;
  company_size: string;
  decision_actor: string;
  constraints: string[];
  extra?: string;
}

export interface GeneratedEmail {
  id: string;
  final_email_id: number;
  subject_line: string;
  email: string;
  problemName: string;
  contextName: string;
  validation_scores: ValidationScores;
  attempts: AttemptCounts;
  createdAt: string;
}

export interface ValidationScores {
  [stage: string]: Array<Record<string, number>>;
}

export interface AttemptCounts {
  [stage: string]: number;
}

export type PipelineStage =
  | 'reasoning_state'
  | 'subject_line'
  | 'hook'
  | 'tension'
  | 'transition_question'
  | 'authority'
  | 'cta'
  | 'final_assembly';

// ─── API Request types ───
export interface CreateProblemRequest {
  problem_name: string;
  core_problem: string;
  system: string;
  causal_mechanism: string;
  failure_mode_A: string;
  failure_mode_B: string;
  failure_mode_A_mechanism: string;
  failure_mode_B_mechanism: string;
  contradiction: string;
  business_impact: string;
  solution_mechanism: string;
  solution_actor: string;
}

export interface ProblemResponse {
  problem_id: string | number;
  snapshot: ProblemSnapshot;
}

export interface CreateContextRequest {
  problem_id: string;
  industry: string;
  company_size: string;
  decision_actor: string;
  extra: string;
  constraints: string[];
}

export interface ContextResponse {
  context_id: string | number;
  snapshot: ContextSnapshot;
}

export interface RunPipelineRequest {
  problem_id: string;
  context_id: string | number;
}

// ─── Daily Analytics from backend ───
export interface DailyAnalytics {
  day: string;
  date: string;
  latency: number;
  cost: number;
  retries: number;
  emails: number;
}