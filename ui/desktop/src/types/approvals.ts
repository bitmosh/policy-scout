export interface ApprovalItem {
  approval_id: string;
  request_id: string;
  decision_id: string;
  created_at: string;
  expires_at: string;
  status: string;
  actor: { type: string; name: string } | null;
  command: string;
  cwd: string;
  risk_score: number;
  decision: string;
  reasons: string[];
  recommended_action: string;
  scope: string;
  schema_version: number;
  [key: string]: unknown;
}

export interface ApprovalListData {
  approvals: ApprovalItem[];
}

export interface ApprovalActionData {
  approval_id: string;
  status: string;
}
