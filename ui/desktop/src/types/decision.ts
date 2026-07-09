// SPDX-License-Identifier: Apache-2.0
export type DecisionCheckDecision =
  | "ALLOW"
  | "ALLOW_LOGGED"
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
  recommended_next_action?: string | null;
  confidence?: number;
  registry_hits?: DecisionCheckRegistryHit[];
  policy_hits?: string[];
  [key: string]: unknown;
}
