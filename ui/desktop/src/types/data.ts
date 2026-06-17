export interface DataPathInfo {
  path: string;
  exists: boolean;
  [key: string]: unknown;
}

export interface DataStatusData {
  data_directory?: string;
  data_root?: string;
  audit_db_path?: string;
  audit_db_size_bytes?: number;
  audit_db_record_count?: number;
  report_directory?: string;
  report_count?: number;
  counts?: Record<string, number>;
  paths?: Record<string, DataPathInfo>;
}

export interface CleanupItem {
  path?: string;
  size_bytes?: number;
  [key: string]: unknown;
}

export interface CouldNotVerifyItem {
  check?: string;
  reason?: string;
  [key: string]: unknown;
}

export interface CleanupDryRunData {
  target?: string;
  dry_run?: boolean;
  total_items?: number;
  total_bytes?: number;
  planned_items?: CleanupItem[];
  could_not_verify?: (string | CouldNotVerifyItem)[];
  schema_version?: number;
}

export interface CleanupResultItem {
  path: string;
  size_bytes?: number;
  reason?: string;
}

export interface CleanupApplyData {
  target: string;
  executed: boolean;
  target_root: string;
  deleted_count: number;
  failed_count: number;
  freed_bytes: number;
  deleted_items: CleanupResultItem[];
  failed_items: CleanupResultItem[];
}
