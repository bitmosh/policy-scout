import { CliJsonResponse } from "../types";

interface AuditStatsCardProps {
  auditStats: CliJsonResponse | null;
}

export function AuditStatsCard({ auditStats }: AuditStatsCardProps) {
  return (
    <div className="audit-card">
      <div className="card-header">
        <h2>Audit Stats</h2>
      </div>

      {auditStats && auditStats.ok && auditStats.data && (
        <div className="audit-data">
          <div className="info-row">
            <span className="label">Total Events:</span>
            <span className="value">{auditStats.data.total_events}</span>
          </div>

          <h3>By Type</h3>
          {auditStats.data.by_type && (
            <div className="counts-list">
              {Object.entries(auditStats.data.by_type).map(([key, value]: [string, any]) => (
                <div key={key} className="count-item">
                  <span className="count-name">{key}</span>
                  <span className="count-value">{value}</span>
                </div>
              ))}
            </div>
          )}

          <h3>Time Range</h3>
          {auditStats.data.time_range && (
            <div className="info-row">
              <span className="label">First Event:</span>
              <span className="value">{auditStats.data.time_range.first_event}</span>
            </div>
          )}
          {auditStats.data.time_range && (
            <div className="info-row">
              <span className="label">Last Event:</span>
              <span className="value">{auditStats.data.time_range.last_event}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
