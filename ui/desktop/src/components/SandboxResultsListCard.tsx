// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, ReportListData, ReportListItem } from "../types";

const LIMIT_OPTIONS = [5, 10, 25, 50];

interface SandboxResultsListCardProps {
  sandboxResults: CliJsonResponse<ReportListData> | null;
  onResultClick?: (reportId: string) => void;
  loading?: boolean;
  limit: number;
  onLimitChange: (limit: number) => void;
  offset?: number;
  totalCount?: number;
  onPagePrev?: () => void;
  onPageNext?: () => void;
}

export function SandboxResultsListCard({
  sandboxResults,
  onResultClick,
  loading = false,
  limit,
  onLimitChange,
  offset = 0,
  totalCount,
  onPagePrev,
  onPageNext,
}: SandboxResultsListCardProps) {
  const results: ReportListItem[] = sandboxResults?.data?.reports ?? [];
  const showing = results.length;
  const from = offset + 1;
  const to = offset + showing;

  return (
    <div className="reports-card">
      <div className="card-header">
        <h2>Sandbox Results</h2>
        <div className="list-controls">
          <div className="list-control-group">
            <label className="list-control-label">Limit</label>
            <select
              className="list-control-select"
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              disabled={loading}
            >
              {LIMIT_OPTIONS.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
          <span className="read-only-label">read-only · Migration is not available from this UI.</span>
        </div>
      </div>

      {loading && <p className="status-message">Loading sandbox results...</p>}

      {!loading && sandboxResults?.ok && (
        <div className="reports-data">
          {results.length > 0 ? (
            <>
              <div className="reports-list">
                {results.map((item: ReportListItem, index: number) => (
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
              {(onPagePrev || onPageNext) && (
                <div className="pagination-controls">
                  {totalCount !== undefined && (
                    <span className="pagination-label">
                      {from}–{to} of {totalCount}
                    </span>
                  )}
                  <button
                    className="pagination-btn"
                    onClick={onPagePrev}
                    disabled={!onPagePrev || offset === 0}
                  >
                    ← Prev
                  </button>
                  <button
                    className="pagination-btn"
                    onClick={onPageNext}
                    disabled={!onPageNext || (totalCount !== undefined && to >= totalCount)}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          ) : (
            <p className="empty-message">No sandbox results found. Run <code>policy-scout sandbox</code> to generate results.</p>
          )}
        </div>
      )}

      {!loading && sandboxResults && !sandboxResults.ok && (
        <p className="error-message">
          Could not load sandbox results{sandboxResults.error ? `: ${sandboxResults.error}` : ""}
        </p>
      )}
    </div>
  );
}
