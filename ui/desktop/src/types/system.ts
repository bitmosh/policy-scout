export interface LockdownStatusData {
  active: boolean;
  reason: string | null;
}

export interface WatchStatusData {
  running: boolean;
  pid: number | null;
  pid_file: string;
  stale?: boolean;
}

export interface SystemHealthData {
  lockdown: LockdownStatusData | null;
  watch: WatchStatusData | null;
}
