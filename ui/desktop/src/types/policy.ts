// SPDX-License-Identifier: Apache-2.0
export interface PolicyRule {
  id: string;
  priority: number;
  decision: string;
  status: string;
  source?: string;
  [key: string]: unknown;
}

export interface PolicyOverviewData {
  registry_version?: number;
  rules?: PolicyRule[];
  override_path?: string | null;
  override_active?: boolean;
  [key: string]: unknown;
}

export interface PolicyIssue {
  issue_type: string;
  description: string;
  severity: string;
  rule_id?: string | null;
  related_rule_id?: string | null;
  [key: string]: unknown;
}

export interface PolicyValidateData {
  rules_checked?: number;
  eval_cases_checked?: number;
  error_count?: number;
  warning_count?: number;
  is_valid?: boolean;
  issues?: PolicyIssue[];
  [key: string]: unknown;
}

export interface RuleTrace {
  rule_id: string;
  source: string;
  priority: number;
  checked: boolean;
  matched: boolean;
  reasons: string[];
  decision: string | null;
  decisive: boolean;
}

export interface PolicySimulateData {
  command: string;
  decision: string;
  risk_score: number;
  risk_band: string;
  matched_rule: string | null;
  categories: string[];
  capabilities: string[];
  confidence: number;
  project_override_loaded: boolean;
  project_override_path: string | null;
  total_rules_checked: number;
  rule_traces: RuleTrace[];
}
