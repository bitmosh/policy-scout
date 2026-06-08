import { CliJsonResponse } from "../types";
import { StatusPill, healthStatusToTone } from "./StatusPill";

interface OverviewStatusStripProps {
  doctorStatus: CliJsonResponse | null;
  reportsList: CliJsonResponse | null;
  auditStats: CliJsonResponse | null;
  demoCleanup: CliJsonResponse | null;
  sandboxCleanup: CliJsonResponse | null;
  sandboxResultsCleanup: CliJsonResponse | null;
  evalResults: CliJsonResponse | null;
  quickSweep: CliJsonResponse | null;
}

export function OverviewStatusStrip({
  doctorStatus,
  reportsList,
  auditStats,
  demoCleanup,
  sandboxCleanup,
  sandboxResultsCleanup,
  evalResults,
  quickSweep,
}: OverviewStatusStripProps) {
  // Health status from doctor
  const getHealthStatus = () => {
    if (!doctorStatus?.ok) return "Error";
    if (!doctorStatus?.data) return "Unknown";
    const checks = doctorStatus.data.checks as any;
    if (!checks) return "Unknown";
    
    const entries = Object.entries(checks) as [string, any][];
    if (entries.length === 0) return "Unknown";
    
    const hasError = entries.some(([_, check]) => check.status === "error");
    const hasWarning = entries.some(([_, check]) => check.status === "warning");
    
    if (hasError) return "Error";
    if (hasWarning) return "Warning";
    return "OK";
  };

  // Reports count
  const getReportsCount = () => {
    if (!reportsList?.ok || !reportsList?.data) return "Unknown";
    const reports = reportsList.data.reports as any[];
    if (!reports) return "Unknown";
    return reports.length.toString();
  };

  // Audit events total
  const getAuditEvents = () => {
    if (!auditStats?.ok || !auditStats?.data) return "Unknown";
    const stats = auditStats.data;
    if (stats.total_events !== undefined) return stats.total_events.toString();
    return "Unknown";
  };

  // Eval pass rate or failed count
  const getEvalStatus = () => {
    if (!evalResults?.ok || !evalResults?.data) return "Unknown";
    const data = evalResults.data;
    if (data.pass_rate !== undefined) return `${data.pass_rate}%`;
    if (data.failed !== undefined) return `${data.failed} failed`;
    return "Unknown";
  };

  // Cleanup dry-run total items
  const getCleanupTotal = () => {
    let total = 0;
    let hasData = false;

    if (demoCleanup?.ok && demoCleanup?.data) {
      const planned = demoCleanup.data.planned_items as any[];
      if (planned) {
        total += planned.length;
        hasData = true;
      }
    }

    if (sandboxCleanup?.ok && sandboxCleanup?.data) {
      const planned = sandboxCleanup.data.planned_items as any[];
      if (planned) {
        total += planned.length;
        hasData = true;
      }
    }

    if (sandboxResultsCleanup?.ok && sandboxResultsCleanup?.data) {
      const planned = sandboxResultsCleanup.data.planned_items as any[];
      if (planned) {
        total += planned.length;
        hasData = true;
      }
    }

    if (!hasData) return "Unknown";
    return total.toString();
  };

  // Quick Sweep status
  const getQuickSweepStatus = () => {
    if (!quickSweep) return "Not run";
    if (!quickSweep.ok) return "Error";
    if (!quickSweep.data) return "Unknown";
    
    const findings = quickSweep.data.findings as any[];
    const couldNotVerify = quickSweep.data.could_not_verify as any[];
    
    if (!findings && !couldNotVerify) return "No findings";
    
    const parts: string[] = [];
    if (findings && findings.length > 0) {
      parts.push(`${findings.length} findings`);
    }
    if (couldNotVerify && couldNotVerify.length > 0) {
      parts.push(`${couldNotVerify.length} could not verify`);
    }
    
    return parts.length > 0 ? parts.join(", ") : "No findings";
  };

  const healthStatus = getHealthStatus();
  const reportsCount = getReportsCount();
  const auditEvents = getAuditEvents();
  const evalStatus = getEvalStatus();
  const cleanupTotal = getCleanupTotal();
  const quickSweepStatus = getQuickSweepStatus();

  return (
    <div className="status-strip">
      <StatusPill label="Health" tone={healthStatusToTone(healthStatus)} value={healthStatus} />
      <StatusPill label="Reports" tone="neutral" value={reportsCount} />
      <StatusPill label="Audit Events" tone="neutral" value={auditEvents} />
      <StatusPill label="Eval" tone="neutral" value={evalStatus} />
      <StatusPill label="Cleanup Preview" tone="neutral" value={`${cleanupTotal} items`} />
      <StatusPill label="Quick Sweep" tone="neutral" value={quickSweepStatus} />
    </div>
  );
}
