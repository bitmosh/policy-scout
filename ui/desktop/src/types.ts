// Generic CLI JSON response wrapper
export interface CliJsonResponse<T = any> {
  ok: boolean;
  exit_code: number;
  data: T;
  error: string | null;
  stderr_summary: string | null;
}

// Type guards and helpers
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? value : [];
}

export function isCliSuccess<T = unknown>(response: CliJsonResponse<T>): response is CliJsonResponse<T> {
  return response.ok === true && response.exit_code === 0;
}

// Report type allowlist (mirrors Rust ALLOWED_REPORT_TYPES)
export type ReportType =
  | "command_decision"
  | "sandbox_result"
  | "project_sweep"
  | "system_quick_sweep";

// Empty string = no filter (all report types)
export type ReportTypeFilter = ReportType | "";

// Audit event type allowlist (mirrors Rust ALLOWED_AUDIT_EVENT_TYPES)
export type AuditEventType =
  | "SweepCompleted"
  | "SweepError"
  | "SandboxInstallCompleted"
  | "SandboxInstallStarted"
  | "SandboxResultWritten"
  | "ScoutReportGenerated"
  | "CommandExecutionCompleted"
  | "CommandExecutionBlocked"
  | "ApprovalRequested"
  | "ApprovalApprovedOnce"
  | "ApprovalDeniedOnce"
  | "DecisionIssued";

// "all" = no filter (recent audit list)
export type AuditEventTypeFilter = AuditEventType | "all";

// Cleanup target allowlist (mirrors Rust ALLOWED_CLEANUP_TARGETS)
export type CleanupTarget = "demo" | "sandbox" | "sandbox-results";

// Doctor Status
export interface DoctorStatusData {
  policy_scout_version?: string;
  python_version?: string;
  platform?: {
    system?: string;
    release?: string;
    version?: string;
    machine?: string;
    processor?: string;
  };
  checks?: Record<string, {
    status: string;
    message: string;
    [key: string]: unknown;
  }>;
}

// Data Status
export interface DataStatusData {
  data_directory?: string;
  data_root?: string;
  audit_db_path?: string;
  audit_db_size_bytes?: number;
  audit_db_record_count?: number;
  report_directory?: string;
  report_count?: number;
  counts?: Record<string, number>;
  paths?: Record<string, { exists?: boolean; [key: string]: unknown }>;
  [key: string]: unknown;
}

// Report List
export interface ReportListItem {
  report_id: string;
  created_at?: string;
  updated_at?: string;
  findings_count?: number;
  severity_distribution?: Record<string, number>;
  [key: string]: unknown;
}

export interface ReportListData {
  reports?: ReportListItem[];
  total_count?: number;
  [key: string]: unknown;
}

// Sandbox Result List
export interface SandboxResultListItem {
  report_id?: string;
  report_type?: string;
  title?: string;
  created_at?: string;
  has_json?: boolean;
  has_markdown?: boolean;
  [key: string]: unknown;
}

// Sandbox Result Detail
export interface SandboxResultDetailData {
  report_id?: string;
  report_type?: string;
  title?: string;
  created_at?: string;
  request_id?: string;
  summary?: string;
  command?: string;
  sandbox_id?: string;
  exit_code?: number;
  duration_ms?: number;
  lifecycle_scripts?: string[];
  manifest_changed?: boolean;
  lockfile_changed?: boolean;
  files_changed?: string[];
  findings?: unknown[];
  recommended_actions?: string[];
  could_not_verify?: string[];
  host_mutation_status?: string;
  migration_status?: string;
  credential_exposure_assessment?: CredentialExposureAssessment;
  redaction_applied?: boolean;
  [key: string]: unknown;
}

// Report Detail
export interface SweepFinding {
  finding_id?: string;
  sweep_id?: string;
  severity?: string;
  confidence?: string;
  category?: string;
  title?: string;
  location?: string;
  evidence_ref?: string;
  why_it_matters?: string;
  recommended_action?: string;
  schema_version?: number;
  [key: string]: unknown;
}

export interface CouldNotVerifyItem {
  check?: string;
  reason?: string;
  [key: string]: unknown;
}

export interface CredentialExposureAssessment {
  level?: string;
  exposure_detected?: boolean;
  exposure_type?: string;
  notes?: string;
  [key: string]: unknown;
}

export interface ReportDetailData {
  report_id?: string;
  report_type?: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
  request_id?: string;
  summary?: string;
  findings?: SweepFinding[];
  findings_count?: Record<string, number>;
  could_not_verify?: (string | CouldNotVerifyItem)[];
  recommended_actions?: (string | unknown)[];
  credential_exposure_assessment?: CredentialExposureAssessment;
  host_mutation_status?: string;
  migration_status?: string;
  sweep_id?: string;
  project_root?: string;
  redaction_applied?: boolean;
  schema_version?: number;
  [key: string]: unknown;
}

// Audit Stats
export interface AuditStatsData {
  total_events?: number;
  events_by_decision?: Record<string, number>;
  events_by_category?: Record<string, number>;
  by_type?: Record<string, number>;
  time_range?: {
    first_event?: string;
    last_event?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

// Audit Event List
export interface AuditEventListItem {
  event_id: string;
  timestamp?: string;
  decision?: string;
  category?: string;
  [key: string]: unknown;
}

export interface AuditEventListData {
  events?: AuditEventListItem[];
  total_count?: number;
  [key: string]: unknown;
}

// Audit Event Detail
export interface AuditEventDetailData {
  event_id?: string;
  event_type?: string;
  timestamp?: string;
  decision?: string;
  category?: string;
  summary?: string;
  data_json?: string;
  redaction_applied?: boolean;
  schema_version?: number;
  request_id?: string;
  actor_type?: string;
  actor_name?: string;
  decision_id?: string;
  approval_id?: string;
  sandbox_id?: string;
  sweep_id?: string;
  report_id?: string;
  execution_id?: string;
  created_at?: string;
  [key: string]: unknown;
}

// Cleanup Dry Run
export interface CleanupItem {
  path?: string;
  size_bytes?: number;
  [key: string]: unknown;
}

export interface CleanupDryRunData {
  target?: string;
  dry_run?: boolean;
  total_items?: number;
  total_bytes?: number;
  planned_items?: CleanupItem[];
  could_not_verify?: (string | CouldNotVerifyItem)[];
  schema_version?: number;
  [key: string]: unknown;
}

// Eval Run
export interface EvalSummary {
  total_cases?: number;
  passed?: number;
  failed?: number;
  pass_rate?: number;
  duration_ms?: number;
  execution_time_ms?: number;
  failed_case_ids?: string[];
  [key: string]: unknown;
}

export interface EvalRunData {
  summary?: EvalSummary;
  cases?: Array<{
    case_id?: string;
    status?: string;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}

// Sweep
export interface SweepData {
  sweep_id?: string;
  sweep_type?: string;
  started_at?: string;
  completed_at?: string;
  project_root?: string;
  platform?: string;
  findings_count?: Record<string, number>;
  findings?: SweepFinding[];
  could_not_verify?: (string | CouldNotVerifyItem)[];
  schema_version?: number;
  [key: string]: unknown;
}

// Decision Check
export type DecisionCheckDecision =
  | "ALLOW"
  | "REQUIRE_APPROVAL"
  | "SANDBOX_FIRST"
  | "DENY"
  | "DENY_AND_ALERT";

export type DecisionCheckRiskBand = "low" | "medium" | "high" | "critical";

export interface DecisionCheckRegistryHit {
  registry_name?: string;
  entry_id?: string;
  confidence?: number;
  metadata?: Record<string, unknown>;
}

export interface DecisionCheckData {
  request_id?: string;
  command: string;
  decision: DecisionCheckDecision;
  risk_score: number;
  risk_band: DecisionCheckRiskBand;
  category: string;
  capabilities: string[];
  reasons: string[];
  recommended_next_action?: string;
  confidence?: number;
  registry_hits?: DecisionCheckRegistryHit[];
  policy_hits?: string[];
  [key: string]: unknown;
}

// Guided FAQ
export type GuidedFaqCategory =
  | "command_safety"
  | "package_installs"
  | "sandbox_workflow"
  | "cleanup_dry_run"
  | "sweep_findings"
  | "reports_audit"
  | "approvals"
  | "credential_hygiene"
  | "troubleshooting"
  | "dashboard_navigation";

export interface GuidedFaqPrompt {
  id: string;
  category: GuidedFaqCategory;
  label: string;
  description: string;
  exampleCommand?: string;
  explanation: string;
  safetyNote?: string;
}
