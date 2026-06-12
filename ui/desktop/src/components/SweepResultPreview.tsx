import { useState } from "react";
import { StatusPill, severityToTone, confidenceToTone } from "./StatusPill";
import { EvidenceText } from "./EvidenceText";
import { SweepData, SweepFinding, CouldNotVerifyItem, asArray } from "../types";

const SEVERITY_OPTIONS = ["all", "critical", "high", "medium", "low", "info"] as const;
type SeverityFilter = typeof SEVERITY_OPTIONS[number];

interface SweepResultPreviewProps {
  data: SweepData | undefined;
  maxFindings?: number;
  maxCouldNotVerify?: number;
  showProjectRoot?: boolean;
}

export function SweepResultPreview({
  data,
  maxFindings = 10,
  maxCouldNotVerify = 5,
  showProjectRoot = false,
}: SweepResultPreviewProps) {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");

  if (!data) return null;

  const findings = asArray<SweepFinding>(data.findings);
  const couldNotVerify = asArray<string | CouldNotVerifyItem>(data.could_not_verify);
  const findingsCount = findings.length;
  const couldNotVerifyCount = couldNotVerify.length;

  const filteredFindings = severityFilter === "all"
    ? findings
    : findings.filter((f) => (f.severity ?? "").toLowerCase() === severityFilter);
  const visibleFindings = filteredFindings.slice(0, maxFindings);
  const truncated = filteredFindings.length > maxFindings;

  return (
    <>
      <div className="sweep-summary">
        <div className="info-row">
          <span className="info-label">Sweep ID:</span>
          <span className="info-value">{data.sweep_id || "N/A"}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Sweep Type:</span>
          <span className="info-value">{data.sweep_type || "N/A"}</span>
        </div>
        {showProjectRoot && (
          <div className="info-row">
            <span className="info-label">Project Root:</span>
            <span className="info-value"><EvidenceText text={data.project_root || "N/A"} /></span>
          </div>
        )}
        <div className="info-row">
          <span className="info-label">Findings:</span>
          <span className="info-value">{findingsCount}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Could Not Verify:</span>
          <span className="info-value">{couldNotVerifyCount}</span>
        </div>
        {data.schema_version && (
          <div className="info-row">
            <span className="info-label">Schema Version:</span>
            <span className="info-value">{data.schema_version}</span>
          </div>
        )}
      </div>

      {findingsCount > 0 && (
        <div className="sweep-findings">
          <div className="sweep-findings-header">
            <h3>Findings (Review Recommended)</h3>
            <div className="list-control-group">
              <label className="list-control-label">Severity:</label>
              <select
                className="list-control-select"
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
              >
                {SEVERITY_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s === "all" ? `All (${findingsCount})` : `${s.charAt(0).toUpperCase() + s.slice(1)} (${findings.filter((f) => (f.severity ?? "").toLowerCase() === s).length})`}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="finding-note">
            These are evidence-gathering results, not confirmed compromises.
          </p>
          <div className="findings-list">
            {visibleFindings.length > 0 ? visibleFindings.map((finding, index) => (
              <div key={index} className="finding-item">
                <div className="finding-header">
                  <StatusPill
                    label=""
                    tone={severityToTone(finding.severity ?? "")}
                    value={finding.severity?.toUpperCase()}
                    className="finding-severity-pill"
                  />
                  <StatusPill
                    label=""
                    tone={confidenceToTone(finding.confidence ?? "")}
                    value={`${finding.confidence?.toUpperCase()} confidence`}
                    className="finding-confidence-pill"
                  />
                </div>
                <div className="finding-category">{finding.category}</div>
                <div className="finding-title"><EvidenceText text={finding.title ?? ""} /></div>
                {finding.location && (
                  <div className="finding-location"><EvidenceText text={finding.location ?? ""} className="finding-location" /></div>
                )}
              </div>
            )) : (
              <p className="empty-message">No {severityFilter} findings.</p>
            )}
            {truncated && (
              <p className="findings-truncated">
                Showing first {maxFindings} of {filteredFindings.length}{severityFilter !== "all" ? ` ${severityFilter}` : ""} findings — run from CLI for full results.
              </p>
            )}
          </div>
        </div>
      )}

      {couldNotVerifyCount > 0 && (
        <div className="sweep-could-not-verify">
          <h3>Could Not Verify</h3>
          <div className="could-not-verify-list">
            {couldNotVerify.slice(0, maxCouldNotVerify).map((item, index) => (
              <div key={index} className="could-not-verify-item">
                <div className="could-not-verify-check"><EvidenceText text={typeof item === "string" ? item : (item.check ?? "Unknown check")} /></div>
                {typeof item === "object" && item.reason && (
                  <div className="could-not-verify-reason"><EvidenceText text={item.reason} /></div>
                )}
              </div>
            ))}
            {couldNotVerifyCount > maxCouldNotVerify && (
              <p className="could-not-verify-truncated">
                Showing first {maxCouldNotVerify} of {couldNotVerifyCount} checks — run from CLI for full results.
              </p>
            )}
          </div>
        </div>
      )}

      {findingsCount === 0 && couldNotVerifyCount === 0 && (
        <p className="status-message">No findings or verification issues detected.</p>
      )}
    </>
  );
}
