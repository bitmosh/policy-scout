import type { CredentialExposureAssessment, SweepFinding } from "./reports";
import type { CouldNotVerifyItem } from "./data";

export interface SandboxLifecycleScript {
  package_name: string;
  script_name: string;
  script_content: string;
  location: string;
}

export interface SandboxLaunchResultData {
  sandbox_id: string;
  request_id: string;
  command: string;
  package_manager: string;
  temp_workspace: string;
  host_project_root: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  exit_code: number;
  stdout: string;
  stderr: string;
  manifest_changed: boolean;
  lockfile_changed: boolean;
  lifecycle_scripts_found: SandboxLifecycleScript[];
  findings: SweepFinding[];
  migration_available: boolean;
  migration_requires_approval: boolean;
  schema_version: number;
  [key: string]: unknown;
}

export interface SandboxMigrationData {
  migration_id: string;
  sandbox_id: string;
  request_id: string;
  started_at: string;
  completed_at: string;
  host_project_root: string;
  sandbox_workspace: string;
  files_planned: string[];
  files_migrated: string[];
  files_skipped: string[];
  backups_created: string[];
  blocked: boolean;
  block_reasons: string[];
  success: boolean;
  schema_version: number;
}

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
