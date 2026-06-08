import { StatusPill, severityToTone, confidenceToTone } from "./StatusPill";
import { EvidenceText } from "./EvidenceText";

interface SweepResultPreviewProps {
  data: any;
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
  if (!data) return null;

  const findings = data.findings as any[] || [];
  const couldNotVerify = data.could_not_verify as any[] || [];
  const findingsCount = findings.length;
  const couldNotVerifyCount = couldNotVerify.length;

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
          <h3>Findings (Review Recommended)</h3>
          <p className="finding-note">
            These are evidence-gathering results, not confirmed compromises.
          </p>
          <div className="findings-list">
            {findings.slice(0, maxFindings).map((finding: any, index: number) => (
              <div key={index} className="finding-item">
                <div className="finding-header">
                  <StatusPill
                    label=""
                    tone={severityToTone(finding.severity)}
                    value={finding.severity?.toUpperCase()}
                    className="finding-severity-pill"
                  />
                  <StatusPill
                    label=""
                    tone={confidenceToTone(finding.confidence)}
                    value={`${finding.confidence?.toUpperCase()} confidence`}
                    className="finding-confidence-pill"
                  />
                </div>
                <div className="finding-category">{finding.category}</div>
                <div className="finding-title"><EvidenceText text={finding.title} /></div>
                {finding.location && (
                  <div className="finding-location"><EvidenceText text={finding.location} className="finding-location" /></div>
                )}
              </div>
            ))}
            {findingsCount > maxFindings && (
              <p className="findings-truncated">
                ... and {findingsCount - maxFindings} more findings
              </p>
            )}
          </div>
        </div>
      )}

      {couldNotVerifyCount > 0 && (
        <div className="sweep-could-not-verify">
          <h3>Could Not Verify</h3>
          <div className="could-not-verify-list">
            {couldNotVerify.slice(0, maxCouldNotVerify).map((item: any, index: number) => (
              <div key={index} className="could-not-verify-item">
                <div className="could-not-verify-check"><EvidenceText text={typeof item === "string" ? item : item.check || "Unknown check"} /></div>
                {typeof item === "object" && item.reason && (
                  <div className="could-not-verify-reason"><EvidenceText text={item.reason} /></div>
                )}
              </div>
            ))}
            {couldNotVerifyCount > maxCouldNotVerify && (
              <p className="could-not-verify-truncated">
                ... and {couldNotVerifyCount - maxCouldNotVerify} more checks
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
