import { CliJsonResponse } from "../types";

interface EvalResultsCardProps {
  evalResults: CliJsonResponse | null;
}

export function EvalResultsCard({ evalResults }: EvalResultsCardProps) {
  if (!evalResults || !evalResults.ok || !evalResults.data) {
    return null;
  }

  const summary = evalResults.data.summary;
  if (!summary) {
    return null;
  }

  const totalCases = summary.total_cases || 0;
  const passed = summary.passed || 0;
  const failed = summary.failed || 0;
  const passRate = summary.pass_rate !== undefined ? (summary.pass_rate * 100).toFixed(1) + "%" : "N/A";
  const duration = summary.duration_ms || summary.execution_time_ms || 0;
  const failedCaseIds = summary.failed_case_ids || [];

  const statusColor = failed === 0 ? "#28a745" : "#dc3545";
  const statusText = failed === 0 ? "All Passed" : `${failed} Failed`;

  return (
    <div className="eval-card">
      <div className="card-header">
        <h2>Policy Eval Health</h2>
      </div>

      <div className="eval-summary">
        <div className="info-row">
          <span className="label">Total Cases:</span>
          <span className="value">{totalCases}</span>
        </div>
        <div className="info-row">
          <span className="label">Passed:</span>
          <span className="value">{passed}</span>
        </div>
        <div className="info-row">
          <span className="label">Failed:</span>
          <span className="value">{failed}</span>
        </div>
        <div className="info-row">
          <span className="label">Pass Rate:</span>
          <span className="value">{passRate}</span>
        </div>
        <div className="info-row">
          <span className="label">Duration:</span>
          <span className="value">{duration}ms</span>
        </div>
      </div>

      <div className="eval-status" style={{ color: statusColor }}>
        <strong>{statusText}</strong>
      </div>

      {failedCaseIds.length > 0 && (
        <div className="eval-failed">
          <h4>Failed Cases</h4>
          <div className="failed-list">
            {failedCaseIds.slice(0, 5).map((caseId: string, index: number) => (
              <div key={index} className="failed-item">
                {caseId}
              </div>
            ))}
            {failedCaseIds.length > 5 && (
              <div className="failed-remaining">
                ... and {failedCaseIds.length - 5} more
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
