export interface RunGateExecutionData {
  execution_id: string;
  request_id: string;
  decision_id: string;
  command: string;
  cwd: string;
  route: string;
  started_at: string;
  completed_at: string | null;
  exit_code: number | null;
  duration_ms: number | null;
  stdout: string | null;
  stderr: string | null;
  schema_version: number;
}

export interface RunGateBlockedData {
  decision: string;
  decision_id: string;
  risk_score: number;
  risk_band: string;
  category: string;
  reasons: string[];
  command: string;
  approval_id?: string;
}

export type RunGateData = RunGateExecutionData | RunGateBlockedData;
