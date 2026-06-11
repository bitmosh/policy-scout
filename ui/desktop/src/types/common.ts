export interface CliJsonResponse<T = unknown> {
  ok: boolean;
  exit_code: number;
  data: T;
  error: string | null;
  stderr_summary: string | null;
}

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export function isCliSuccess<T = unknown>(
  response: CliJsonResponse<T>
): response is CliJsonResponse<T> {
  return response.ok === true && response.exit_code === 0;
}

export type ReportType =
  | "command_decision"
  | "sandbox_result"
  | "project_sweep"
  | "system_quick_sweep";

export type ReportTypeFilter = ReportType | "";

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

export type AuditEventTypeFilter = AuditEventType | "all";

export type CleanupTarget = "demo" | "sandbox" | "sandbox-results";
