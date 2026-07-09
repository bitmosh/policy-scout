// SPDX-License-Identifier: Apache-2.0
import type { SweepFinding } from "./reports";
import type { CouldNotVerifyItem } from "./data";

export interface SweepData {
  sweep_id?: string;
  sweep_type?: string;
  started_at?: string;
  completed_at?: string;
  project_root?: string;
  platform?: string;
  findings_count?: Record<string, number>;
  findings?: SweepFinding[];
  could_not_verify?: (string | CouldNotVerifyItem)[];
  schema_version?: number;
  [key: string]: unknown;
}
