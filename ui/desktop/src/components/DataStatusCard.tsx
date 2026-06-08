import { CliJsonResponse } from "../types";

interface DataStatusCardProps {
  dataStatus: CliJsonResponse | null;
}

export function DataStatusCard({ dataStatus }: DataStatusCardProps) {
  return (
    <div className="data-card">
      <div className="card-header">
        <h2>Data Status</h2>
      </div>

      {dataStatus && dataStatus.ok && dataStatus.data && (
        <div className="data-data">
          <div className="info-row">
            <span className="label">Data Root:</span>
            <span className="value">{dataStatus.data.data_root}</span>
          </div>

          <h3>Counts</h3>
          {dataStatus.data.counts && (
            <div className="counts-list">
              {Object.entries(dataStatus.data.counts).map(([key, value]: [string, any]) => (
                <div key={key} className="count-item">
                  <span className="count-name">{key}</span>
                  <span className="count-value">{value}</span>
                </div>
              ))}
            </div>
          )}

          <h3>Paths</h3>
          {dataStatus.data.paths && (
            <div className="paths-list">
              {Object.entries(dataStatus.data.paths).map(([key, path]: [string, any]) => (
                <div key={key} className={`path-item ${path.exists ? "exists" : "missing"}`}>
                  <span className="path-name">{key}</span>
                  <span className={`path-status ${path.exists ? "exists" : "missing"}`}>
                    {path.exists ? "exists" : "missing"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
