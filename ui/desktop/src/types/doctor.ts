// SPDX-License-Identifier: Apache-2.0
export interface DoctorCheck {
  status: string;
  message: string;
  [key: string]: unknown;
}

export interface DoctorStatusData {
  policy_scout_version?: string;
  python_version?: string;
  platform?: {
    system?: string;
    release?: string;
    version?: string;
    machine?: string;
    processor?: string;
  };
  checks?: Record<string, DoctorCheck>;
}
