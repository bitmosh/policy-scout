import { CliJsonResponse, SandboxResultListItem, asArray } from "../types";

interface SandboxResultsListCardProps {
  sandboxResults: CliJsonResponse<SandboxResultListItem[]> | null;
  onResultClick?: (reportId: string) => void;
}

export function SandboxResultsListCard({ sandboxResults, onResultClick }: SandboxResultsListCardProps) {
  const results = asArray<SandboxResultListItem>(sandboxResults?.data);

  return (
    <div className="reports-card">
      <div className="card-header">
        <h2>Sandbox Results</h2>
        <span className="read-only-label">read-only · Migration is not available from this UI.</span>
      </div>

      {sandboxResults && sandboxResults.ok && (
        <div className="reports-data">
          {results.length > 0 ? (
            <div className="reports-list">
              {results.map((item: SandboxResultListItem, index: number) => (
                <div
                  key={item.report_id || index}
                  className={`report-item${onResultClick && item.report_id ? " clickable" : ""}`}
                  onClick={() => onResultClick && item.report_id && onResultClick(item.report_id)}
                >
                  <div className="report-info">
                    <span className="report-id">{item.report_id || "—"}</span>
                    <span className="report-type">{item.report_type || "sandbox_result"}</span>
                  </div>
                  {item.title && (
                    <div className="report-title">{item.title}</div>
                  )}
                  <div className="report-meta">
                    {item.created_at && (
                      <span className="report-created">{item.created_at}</span>
                    )}
                    {(item.has_json || item.has_markdown) && (
                      <span className="report-formats">
                        {item.has_json && <span className="format-badge">JSON</span>}
                        {item.has_markdown && <span className="format-badge">MD</span>}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">No sandbox results found</p>
          )}
        </div>
      )}

      {sandboxResults && !sandboxResults.ok && (
        <p className="error-message">
          Could not load sandbox results{sandboxResults.error ? `: ${sandboxResults.error}` : ""}
        </p>
      )}
    </div>
  );
}
