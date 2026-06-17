import { useState } from "react";
import { CliJsonResponse, CleanupDryRunData, CleanupApplyData, CleanupTarget } from "../types";
import { EvidenceText } from "./EvidenceText";

const CLEANUP_TARGET_OPTIONS: { value: CleanupTarget; label: string }[] = [
  { value: "demo", label: "Demo data" },
  { value: "sandbox", label: "Sandbox workspaces" },
  { value: "sandbox-results", label: "Sandbox results" },
];

interface CleanupDryRunCardProps {
  cleanupResult: CliJsonResponse<CleanupDryRunData> | null;
  cleanupTarget: CleanupTarget;
  onTargetChange: (target: CleanupTarget) => void;
  loading?: boolean;
  onApply: () => void;
  applyResult: CliJsonResponse<CleanupApplyData> | null;
  applyLoading: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
}

export function CleanupDryRunCard({
  cleanupResult,
  cleanupTarget,
  onTargetChange,
  loading,
  onApply,
  applyResult,
  applyLoading,
}: CleanupDryRunCardProps) {
  const [confirming, setConfirming] = useState(false);

  const data = cleanupResult?.ok && cleanupResult?.data ? cleanupResult.data as CleanupDryRunData : null;
  const previewItems = data?.planned_items ? data.planned_items.slice(0, 5) : [];
  const hasItems = (data?.total_items ?? 0) > 0;
  const applied = applyResult != null;

  function handleApplyClick() {
    setConfirming(true);
  }
  function handleConfirm() {
    setConfirming(false);
    onApply();
  }
  function handleCancel() {
    setConfirming(false);
  }

  // Reset confirm state when target changes or new dry-run loads
  function handleTargetChange(t: CleanupTarget) {
    setConfirming(false);
    onTargetChange(t);
  }

  return (
    <div className="cleanup-card">
      <div className="card-header">
        <h2>Data Cleanup</h2>
        <div className="list-controls">
          <div className="list-control-group">
            <label className="list-control-label">Target:</label>
            <select
              className="list-control-select"
              value={cleanupTarget}
              onChange={(e) => handleTargetChange(e.target.value as CleanupTarget)}
              disabled={loading || applyLoading}
            >
              {CLEANUP_TARGET_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {data && (
        <div className="cleanup-sections">
          <div className="cleanup-section">
            <div className="cleanup-info">
              <div className="info-row">
                <span className="label">Target:</span>
                <span className="value">{data.target}</span>
              </div>
              <div className="info-row">
                <span className="label">Total Items:</span>
                <span className="value">{data.total_items}</span>
              </div>
              <div className="info-row">
                <span className="label">Total Size:</span>
                <span className="value">{data.total_bytes !== undefined ? formatBytes(data.total_bytes) : "N/A"}</span>
              </div>
            </div>

            {previewItems.length > 0 && (
              <div className="planned-items">
                <h4>Planned Items (preview)</h4>
                <div className="items-list">
                  {previewItems.map((item, index) => (
                    <div key={index} className="item-row">
                      <span className="item-path"><EvidenceText text={item.path ?? ""} className="item-path" /></span>
                      <span className="item-meta">
                        {item.size_bytes !== undefined ? formatBytes(item.size_bytes) : ""}
                      </span>
                    </div>
                  ))}
                  {data.planned_items && data.planned_items.length > 5 && (
                    <div className="items-remaining">
                      … and {data.planned_items.length - 5} more
                    </div>
                  )}
                </div>
              </div>
            )}

            {data.could_not_verify && data.could_not_verify.length > 0 && (
              <div className="cleanup-unverified">
                <h4>Could Not Verify</h4>
                {data.could_not_verify.map((item, index) => (
                  <div key={index} className="unverified-item">
                    <EvidenceText text={typeof item === "string" ? item : JSON.stringify(item)} />
                  </div>
                ))}
              </div>
            )}

            {/* Apply section — only shown if there are items and no result yet */}
            {!applied && (
              <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--color-border-muted)" }}>
                {!hasItems ? (
                  <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Nothing to delete.</div>
                ) : applyLoading ? (
                  <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Deleting…</div>
                ) : confirming ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 13, color: "var(--color-danger)", fontWeight: 500 }}>
                      Delete {data.total_items} item{data.total_items !== 1 ? "s" : ""} ({formatBytes(data.total_bytes ?? 0)}) permanently?
                    </span>
                    <button
                      onClick={handleConfirm}
                      style={{
                        padding: "5px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer",
                        background: "var(--color-danger)", color: "#fff",
                        border: "none", borderRadius: 6,
                      }}
                    >
                      Confirm delete
                    </button>
                    <button
                      onClick={handleCancel}
                      style={{
                        padding: "5px 14px", fontSize: 12.5, cursor: "pointer",
                        background: "transparent", color: "var(--color-text-muted)",
                        border: "1px solid var(--color-border-muted)", borderRadius: 6,
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={handleApplyClick}
                    style={{
                      padding: "6px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer",
                      background: "var(--color-elevated)", color: "var(--color-danger)",
                      border: "1px solid var(--color-border)", borderRadius: 6,
                    }}
                  >
                    Apply…
                  </button>
                )}
              </div>
            )}

            {/* Result section */}
            {applied && applyResult && (
              <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--color-border-muted)" }}>
                {applyResult.ok && applyResult.data ? (
                  <div>
                    <div style={{ fontSize: 13, color: "var(--color-success)", fontWeight: 600, marginBottom: 8 }}>
                      Deleted {applyResult.data.deleted_count} item{applyResult.data.deleted_count !== 1 ? "s" : ""} · {formatBytes(applyResult.data.freed_bytes)} freed
                    </div>
                    {applyResult.data.failed_count > 0 && (
                      <div style={{ fontSize: 12, color: "var(--color-danger)" }}>
                        {applyResult.data.failed_count} item{applyResult.data.failed_count !== 1 ? "s" : ""} failed to delete
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: "var(--color-danger)" }}>
                    {applyResult.error ?? "Cleanup failed."}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
