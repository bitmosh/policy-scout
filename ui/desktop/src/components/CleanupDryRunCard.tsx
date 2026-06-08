import { CliJsonResponse, CleanupDryRunData } from "../types";
import { EvidenceText } from "./EvidenceText";

interface CleanupDryRunCardProps {
  demoCleanup: CliJsonResponse<CleanupDryRunData> | null;
  sandboxCleanup: CliJsonResponse<CleanupDryRunData> | null;
  sandboxResultsCleanup: CliJsonResponse<CleanupDryRunData> | null;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
}

function CleanupSection({ title, data }: { title: string; data: CliJsonResponse<CleanupDryRunData> | null }) {
  if (!data || !data.ok || !data.data) {
    return null;
  }

  const cleanup = data.data as CleanupDryRunData;
  const previewItems = cleanup.planned_items ? cleanup.planned_items.slice(0, 5) : [];

  return (
    <div className="cleanup-section">
      <h3>{title}</h3>
      <div className="cleanup-info">
        <div className="info-row">
          <span className="label">Target:</span>
          <span className="value">{cleanup.target}</span>
        </div>
        <div className="info-row">
          <span className="label">Dry Run:</span>
          <span className="value">{cleanup.dry_run ? "true" : "false"}</span>
        </div>
        <div className="info-row">
          <span className="label">Total Items:</span>
          <span className="value">{cleanup.total_items}</span>
        </div>
        <div className="info-row">
          <span className="label">Total Size:</span>
          <span className="value">{cleanup.total_bytes !== undefined ? formatBytes(cleanup.total_bytes) : "N/A"}</span>
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
            {cleanup.planned_items && cleanup.planned_items.length > 5 && (
              <div className="items-remaining">
                ... and {cleanup.planned_items.length - 5} more
              </div>
            )}
          </div>
        </div>
      )}

      {cleanup.could_not_verify && cleanup.could_not_verify.length > 0 && (
        <div className="cleanup-unverified">
          <h4>Could Not Verify</h4>
          {cleanup.could_not_verify.map((item: any, index: number) => (
            <div key={index} className="unverified-item"><EvidenceText text={typeof item === "string" ? item : JSON.stringify(item)} /></div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CleanupDryRunCard({
  demoCleanup,
  sandboxCleanup,
  sandboxResultsCleanup,
}: CleanupDryRunCardProps) {
  return (
    <div className="cleanup-card">
      <div className="card-header">
        <h2>Cleanup Dry-Run</h2>
      </div>

      <div className="dry-run-notice">
        <strong>DRY RUN ONLY</strong>
        <p>Preview only. No files are deleted from this UI.</p>
      </div>

      <div className="cleanup-sections">
        <CleanupSection title="Demo Workspaces" data={demoCleanup} />
        <CleanupSection title="Sandbox Workspaces" data={sandboxCleanup} />
        <CleanupSection title="Sandbox Results" data={sandboxResultsCleanup} />
      </div>
    </div>
  );
}
