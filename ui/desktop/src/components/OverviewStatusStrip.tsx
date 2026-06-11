import {
  CliJsonResponse,
  DoctorStatusData,
  AuditStatsData,
  CleanupDryRunData,
  EvalRunData,
  SweepData,
  ReportListData,
} from "../types";
import { StatusPill, healthStatusToTone } from "./StatusPill";

interface OverviewStatusStripProps {
  doctorStatus: CliJsonResponse<DoctorStatusData> | null;
  reportsList: CliJsonResponse<ReportListData> | null;
  auditStats: CliJsonResponse<AuditStatsData> | null;
  cleanupResult: CliJsonResponse<CleanupDryRunData> | null;
  evalResults: CliJsonResponse<EvalRunData> | null;
  quickSweep: CliJsonResponse<SweepData> | null;
}

export function OverviewStatusStrip({
  doctorStatus,
  reportsList,
  auditStats,
  cleanupResult,
  evalResults,
  quickSweep,
}: OverviewStatusStripProps) {
  const getHealthStatus = () => {
    if (!doctorStatus?.ok || !doctorStatus.data?.checks) return "Unknown";
    const entries = Object.entries(doctorStatus.data.checks);
    if (entries.length === 0) return "Unknown";
    const hasError = entries.some(([, check]) => check?.status === "error");
    const hasWarning = entries.some(([, check]) => check?.status === "warning");
    if (hasError) return "Error";
    if (hasWarning) return "Warning";
    return "OK";
  };

  const getReportsCount = () => {
    if (!reportsList?.ok) return "Unknown";
    const totalCount = reportsList.data?.total_count;
    if (totalCount !== undefined) return totalCount.toString();
    const arr = reportsList.data?.reports;
    return Array.isArray(arr) ? arr.length.toString() : "Unknown";
  };

  const getAuditEvents = () => {
    const total = auditStats?.data?.total_events;
    return total !== undefined ? total.toString() : "Unknown";
  };

  const getEvalStatus = () => {
    const summary = evalResults?.data?.summary;
    if (!evalResults?.ok || !summary) return "Unknown";
    if (summary.pass_rate !== undefined) return `${Math.round(summary.pass_rate * 100)}%`;
    if (summary.failed !== undefined) return `${summary.failed} failed`;
    return "Unknown";
  };

  const getCleanupTotal = () => {
    const items = cleanupResult?.data?.planned_items;
    if (!cleanupResult?.ok || !items) return "Unknown";
    return items.length.toString();
  };

  const getQuickSweepStatus = () => {
    if (!quickSweep) return "Not run";
    if (!quickSweep.ok) return "Error";
    const findings = quickSweep.data?.findings ?? [];
    const couldNotVerify = quickSweep.data?.could_not_verify ?? [];
    const parts: string[] = [];
    if (findings.length > 0) parts.push(`${findings.length} findings`);
    if (couldNotVerify.length > 0) parts.push(`${couldNotVerify.length} could not verify`);
    return parts.length > 0 ? parts.join(", ") : "No findings";
  };

  return (
    <div className="status-strip">
      <StatusPill label="Health" tone={healthStatusToTone(getHealthStatus())} value={getHealthStatus()} />
      <StatusPill label="Reports" tone="neutral" value={getReportsCount()} />
      <StatusPill label="Audit Events" tone="neutral" value={getAuditEvents()} />
      <StatusPill label="Eval" tone="neutral" value={getEvalStatus()} />
      <StatusPill label="Cleanup Preview" tone="neutral" value={`${getCleanupTotal()} items`} />
      <StatusPill label="Quick Sweep" tone="neutral" value={getQuickSweepStatus()} />
    </div>
  );
}
