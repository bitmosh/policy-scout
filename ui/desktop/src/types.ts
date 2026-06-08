export interface CliJsonResponse {
  ok: boolean;
  exit_code: number;
  data: any;
  error: string | null;
  stderr_summary: string | null;
}
