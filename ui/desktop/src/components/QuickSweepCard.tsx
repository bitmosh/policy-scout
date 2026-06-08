import { CliJsonResponse } from "../types";
import { StatusPill, severityToTone, confidenceToTone } from "./StatusPill";
import { EvidenceText } from "./EvidenceText";

interface QuickSweepCardProps {
  quickSweep: CliJsonResponse | null;
  loading: boolean;
  onRunSweep: () => void;
}

export function QuickSweepCard({ quickSweep, loading, onRunSweep }: QuickSweepCardProps) {
  const data = quickSweep?.data;
  const findings = data?.findings as any[] || [];
  const couldNotVerify = data?.could_not_verify as any[] || [];
  const findingsCount = findings.length;
  const couldNotVerifyCount = couldNotVerify.length;

  return (
    <div className="card quick-sweep-card">
      <h2>Quick Sweep</h2>
      <p className="card-subtitle">System signal scan (Linux-first, evidence-gathering)</p>

      {!quickSweep && !loading && (
        <button className="sweep-button" onClick={onRunSweep}>
          Run Quick Sweep
        </button>
      )}

      {loading && !quickSweep && (
        <p className="status-message">Running sweep...</p>
      )}

      {quickSweep && (
        <>
          <div className="sweep-summary">
            <div className="info-row">
              <span className="info-label">Sweep ID:</span>
              <span className="info-value">{data?.sweep_id || "N/A"}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Sweep Type:</span>
              <span className="info-value">{data?.sweep_type || "N/A"}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Findings:</span>
              <span className="info-value">{findingsCount}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Could Not Verify:</span>
              <span className="info-value">{couldNotVerifyCount}</span>
            </div>
            {data?.schema_version && (
              <div className="info-row">
                <span className="info-label">Schema Version:</span>
                <span className="info-value">{data.schema_version}</span>
              </div>
            )}
          </div>

          <button className="sweep-button" onClick={onRunSweep}>
            Run Quick Sweep Again
          </button>

          {findingsCount > 0 && (
            <div className="sweep-findings">
              <h3>Findings (Review Recommended)</h3>
              <p className="finding-note">
                These are evidence-gathering results, not confirmed compromises.
              </p>
              <div className="findings-list">
                {findings.slice(0, 10).map((finding: any, index: number) => (
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
                {findingsCount > 10 && (
                  <p className="findings-truncated">
                    ... and {findingsCount - 10} more findings
                  </p>
                )}
              </div>
            </div>
          )}

          {couldNotVerifyCount > 0 && (
            <div className="sweep-could-not-verify">
              <h3>Could Not Verify</h3>
              <div className="could-not-verify-list">
                {couldNotVerify.slice(0, 5).map((item: any, index: number) => (
                  <div key={index} className="could-not-verify-item">
                    <div className="could-not-verify-check"><EvidenceText text={item.check || "Unknown check"} /></div>
                    <div className="could-not-verify-reason"><EvidenceText text={item.reason || "No reason provided"} /></div>
                  </div>
                ))}
                {couldNotVerifyCount > 5 && (
                  <p className="could-not-verify-truncated">
                    ... and {couldNotVerifyCount - 5} more checks
                  </p>
                )}
              </div>
            </div>
          )}

          {findingsCount === 0 && couldNotVerifyCount === 0 && (
            <p className="status-message">No findings or verification issues detected.</p>
          )}
        </>
      )}
    </div>
  );
}
