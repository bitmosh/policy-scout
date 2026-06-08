import { CliJsonResponse, CleanupDryRunData, CleanupTarget } from "../types";
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
}: CleanupDryRunCardProps) {
  const data = cleanupResult?.ok && cleanupResult?.data ? cleanupResult.data as CleanupDryRunData : null;
  const previewItems = data?.planned_items ? data.planned_items.slice(0, 5) : [];

  return (
    <div className="cleanup-card">
      <div className="card-header">
        <h2>Cleanup Dry-Run</h2>
        <div className="list-controls">
          <div className="list-control-group">
            <label className="list-control-label">Target:</label>
            <select
              className="list-control-select"
              value={cleanupTarget}
              onChange={(e) => onTargetChange(e.target.value as CleanupTarget)}
              disabled={loading}
            >
              {CLEANUP_TARGET_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="dry-run-notice">
        <strong>DRY RUN ONLY</strong>
        <p>Preview only. No files are deleted from this UI.</p>
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
                <span className="label">Dry Run:</span>
                <span className="value">{data.dry_run ? "true" : "false"}</span>
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
                  {previewItems.map((item: any, index: number) => (
                    <div key={index} className="item-row">
                      <span className="item-path"><EvidenceText text={item.path} className="item-path" /></span>
                      <span className="item-meta">
                        {item.type} · {formatBytes(item.size_bytes)}
                      </span>
                    </div>
                  ))}
                  {data.planned_items && data.planned_items.length > 5 && (
                    <div className="items-remaining">
                      ... and {data.planned_items.length - 5} more
                    </div>
                  )}
                </div>
              </div>
            )}

            {data.could_not_verify && data.could_not_verify.length > 0 && (
              <div className="cleanup-unverified">
                <h4>Could Not Verify</h4>
                {data.could_not_verify.map((item: any, index: number) => (
                  <div key={index} className="unverified-item"><EvidenceText text={typeof item === "string" ? item : JSON.stringify(item)} /></div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
