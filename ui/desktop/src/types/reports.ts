// SPDX-License-Identifier: Apache-2.0
import type { CouldNotVerifyItem } from "./data";

export interface CredentialExposureAssessment {
  level?: string;
  exposure_detected?: boolean;
  exposure_type?: string;
  notes?: string;
  [key: string]: unknown;
}

export interface SweepFinding {
  finding_id?: string;
  sweep_id?: string;
  severity?: string;
  confidence?: string;
  category?: string;
  title?: string;
  location?: string;
  evidence_ref?: string;
  why_it_matters?: string;
  recommended_action?: string;
  schema_version?: number;
  [key: string]: unknown;
}

export interface ReportListItem {
  report_id: string;
  created_at?: string;
  updated_at?: string;
  has_markdown?: boolean;
  has_json?: boolean;
  report_type?: string;
  title?: string;
  findings_count?: number;
  severity_distribution?: Record<string, number>;
  [key: string]: unknown;
}

export interface ReportListData {
  reports?: ReportListItem[];
  total_count?: number;
  offset?: number;
}

export interface ReportDetailData {
  report_id?: string;
  report_type?: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
  request_id?: string;
  summary?: string;
  findings?: SweepFinding[];
  findings_count?: Record<string, number>;
  could_not_verify?: (string | CouldNotVerifyItem)[];
  recommended_actions?: (string | unknown)[];
  credential_exposure_assessment?: CredentialExposureAssessment;
  host_mutation_status?: string;
  migration_status?: string;
  sweep_id?: string;
  project_root?: string;
  redaction_applied?: boolean;
  schema_version?: number;
  [key: string]: unknown;
}
