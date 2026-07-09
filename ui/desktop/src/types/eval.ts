// SPDX-License-Identifier: Apache-2.0
export interface EvalSummary {
  total_cases?: number;
  passed?: number;
  failed?: number;
  pass_rate?: number;
  duration_ms?: number | null;
  execution_time_ms?: number | null;
  failed_case_ids?: string[];
  [key: string]: unknown;
}

export interface EvalRunData {
  summary?: EvalSummary;
  results?: Array<{
    case_id?: string;
    status?: string;
    duration_ms?: number | null;
    execution_time_ms?: number | null;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}
