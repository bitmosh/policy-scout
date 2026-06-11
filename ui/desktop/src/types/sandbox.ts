import type { CredentialExposureAssessment, SweepFinding } from "./reports";
import type { CouldNotVerifyItem } from "./data";

export interface SandboxResultListItem {
  report_id?: string;
  report_type?: string;
  title?: string;
  created_at?: string;
  has_json?: boolean;
  has_markdown?: boolean;
  [key: string]: unknown;
}

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
  findings?: SweepFinding[];
  recommended_actions?: string[];
  could_not_verify?: (string | CouldNotVerifyItem)[];
  host_mutation_status?: string;
  migration_status?: string;
  credential_exposure_assessment?: CredentialExposureAssessment;
  redaction_applied?: boolean;
  schema_version?: number;
  [key: string]: unknown;
}
