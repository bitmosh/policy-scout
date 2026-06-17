export type SecretScanFinding = {
  secret_type: string;
  service: string;
  severity: "critical" | "high" | "medium" | "low" | string;
  source: string;
  line: number;
  column: number;
  redacted_value: string;
  guidance: string;
};

export type SecretScanData = {
  scan_id: string;
  scan_type: "directory" | "staged" | "history" | string;
  target: string;
  finding_count: number;
  severity_counts: Record<string, number>;
  files_scanned: number;
  commits_scanned: number;
  duration_ms: number;
  errors: string[];
  findings: SecretScanFinding[];
};

export type InjectionFinding = {
  finding_id: string;
  sweep_id: string;
  severity: string;
  confidence: string;
  category: string;
  title: string;
  location: string;
  evidence_ref: string;
  why_it_matters: string;
  recommended_action: string;
  schema_version: number;
};

export type InjectionScanData = {
  target: string;
  finding_count: number;
  findings: InjectionFinding[];
};
