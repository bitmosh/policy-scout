// SPDX-License-Identifier: Apache-2.0
export interface AuditStatsData {
  total_events?: number;
  events_by_decision?: Record<string, number>;
  events_by_category?: Record<string, number>;
  by_type?: Record<string, number>;
  time_range?: {
    first_event?: string;
    last_event?: string;
    [key: string]: unknown;
  } | null;
  [key: string]: unknown;
}

export interface AuditEventListItem {
  event_id: string;
  event_type?: string;
  timestamp?: string;
  request_id?: string | null;
  actor_type?: string | null;
  actor_name?: string | null;
  summary?: string | null;
  data_json?: string | null;
  schema_version?: number;
  created_at?: string;
  decision_id?: string | null;
  approval_id?: string | null;
  sandbox_id?: string | null;
  sweep_id?: string | null;
  report_id?: string | null;
  execution_id?: string | null;
  [key: string]: unknown;
}

export interface AuditEventListData {
  events?: AuditEventListItem[];
  total_count?: number;
  offset?: number;
}

export interface AuditVerifyChainError {
  lineno: number;
  kind: string;
  detail: string;
}

export interface AuditVerifyChainData {
  verified: boolean;
  total_entries: number;
  message: string;
  errors: AuditVerifyChainError[];
}

export interface AuditEventDetailData {
  event_id?: string;
  event_type?: string;
  timestamp?: string;
  decision?: string;
  category?: string;
  summary?: string | null;
  data_json?: string | null;
  redaction_applied?: boolean;
  schema_version?: number;
  request_id?: string | null;
  actor_type?: string | null;
  actor_name?: string | null;
  decision_id?: string | null;
  approval_id?: string | null;
  sandbox_id?: string | null;
  sweep_id?: string | null;
  report_id?: string | null;
  execution_id?: string | null;
  created_at?: string;
  [key: string]: unknown;
}
