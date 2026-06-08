import { CliJsonResponse, SandboxResultDetailData, asArray } from "../types";
import { DetailHeader } from "./DetailHeader";
import { RedactionNotice } from "./RedactionNotice";
import { EvidenceText } from "./EvidenceText";

interface SandboxResultDetailCardProps {
  sandboxResultDetail: CliJsonResponse<SandboxResultDetailData> | null;
  loading: boolean;
  selectedId: string;
  onClose: () => void;
}

export function SandboxResultDetailCard({ sandboxResultDetail, loading, selectedId, onClose }: SandboxResultDetailCardProps) {
  const data = sandboxResultDetail?.data;
  const reportId = data?.report_id || selectedId;

  if (loading) {
    return (
      <div className="report-detail-card">
        <DetailHeader detailType="Sandbox Result" selectedId={selectedId} onClose={onClose} />
        <p className="status-message">Loading sandbox result...</p>
      </div>
    );
  }

  if (!sandboxResultDetail || !sandboxResultDetail.ok || !data) {
    return (
      <div className="report-detail-card">
        <DetailHeader detailType="Sandbox Result" selectedId={selectedId} onClose={onClose} />
        <p className="empty-message">Could not load sandbox result detail</p>
      </div>
    );
  }

  const findings = asArray(data.findings);
  const recommendedActions = asArray<string>(data.recommended_actions);
  const couldNotVerify = asArray<string>(data.could_not_verify);
  const lifecycleScripts = asArray<string>(data.lifecycle_scripts);
  const filesChanged = asArray<string>(data.files_changed);
  const credentialExposure = data.credential_exposure_assessment || null;

  return (
    <div className="report-detail-card">
      <DetailHeader detailType="Sandbox Result" selectedId={reportId} onClose={onClose} />

      <div className="report-detail-content">
        <div className="boundary-note">
          Read-only sandbox result. Migration is not available from this UI.
        </div>

        <RedactionNotice show={data.redaction_applied || false} />

        <div className="report-metadata">
          <div className="info-row">
            <span className="info-label">Report ID:</span>
            <span className="info-value">{data.report_id || "N/A"}</span>
          </div>
          {data.sandbox_id && (
            <div className="info-row">
              <span className="info-label">Sandbox ID:</span>
              <span className="info-value">{data.sandbox_id}</span>
            </div>
          )}
          <div className="info-row">
            <span className="info-label">Report Type:</span>
            <span className="info-value">{data.report_type || "sandbox_result"}</span>
          </div>
          {data.title && (
            <div className="info-row">
              <span className="info-label">Title:</span>
              <span className="info-value">{data.title}</span>
            </div>
          )}
          {data.created_at && (
            <div className="info-row">
              <span className="info-label">Created:</span>
              <span className="info-value">{data.created_at}</span>
            </div>
          )}
          {data.request_id && (
            <div className="info-row">
              <span className="info-label">Request ID:</span>
              <span className="info-value">{data.request_id}</span>
            </div>
          )}
        </div>

        {data.command && (
          <div className="report-section">
            <h3>Command</h3>
            <p className="status-text"><EvidenceText text={data.command} /></p>
          </div>
        )}

        {data.summary && (
          <div className="report-section">
            <h3>Summary</h3>
            <p className="report-summary"><EvidenceText text={data.summary} /></p>
          </div>
        )}

        <div className="report-section">
          <h3>Sandbox Outcome</h3>
          <div className="report-metadata">
            {data.exit_code !== undefined && (
              <div className="info-row">
                <span className="info-label">Exit Code:</span>
                <span className="info-value">{data.exit_code}</span>
              </div>
            )}
            {data.duration_ms !== undefined && (
              <div className="info-row">
                <span className="info-label">Duration:</span>
                <span className="info-value">{data.duration_ms}ms</span>
              </div>
            )}
            {data.manifest_changed !== undefined && (
              <div className="info-row">
                <span className="info-label">Manifest Changed:</span>
                <span className="info-value">{data.manifest_changed ? "Yes" : "No"}</span>
              </div>
            )}
            {data.lockfile_changed !== undefined && (
              <div className="info-row">
                <span className="info-label">Lockfile Changed:</span>
                <span className="info-value">{data.lockfile_changed ? "Yes" : "No"}</span>
              </div>
            )}
          </div>
        </div>

        {filesChanged.length > 0 && (
          <div className="report-section">
            <h3>Files Changed</h3>
            <ul className="actions-list">
              {filesChanged.map((f, i) => (
                <li key={i} className="action-item"><EvidenceText text={f} /></li>
              ))}
            </ul>
          </div>
        )}

        {lifecycleScripts.length > 0 && (
          <div className="report-section">
            <h3>Lifecycle Scripts</h3>
            <ul className="actions-list">
              {lifecycleScripts.map((s, i) => (
                <li key={i} className="action-item"><EvidenceText text={s} /></li>
              ))}
            </ul>
          </div>
        )}

        {findings.length > 0 && (
          <div className="report-section">
            <h3>Findings ({findings.length})</h3>
            <ul className="actions-list">
              {findings.map((f: unknown, i: number) => (
                <li key={i} className="action-item">
                  <EvidenceText text={typeof f === "string" ? f : JSON.stringify(f)} />
                </li>
              ))}
            </ul>
          </div>
        )}

        {recommendedActions.length > 0 && (
          <div className="report-section">
            <h3>Recommended Actions</h3>
            <ul className="actions-list">
              {recommendedActions.map((a, i) => (
                <li key={i} className="action-item"><EvidenceText text={a} /></li>
              ))}
            </ul>
          </div>
        )}

        {couldNotVerify.length > 0 && (
          <div className="report-section">
            <h3>Could Not Verify</h3>
            <ul className="could-not-verify-list">
              {couldNotVerify.map((item, i) => (
                <li key={i} className="could-not-verify-item"><EvidenceText text={item} /></li>
              ))}
            </ul>
          </div>
        )}

        {credentialExposure && (
          <div className="report-section">
            <h3>Credential Exposure Assessment</h3>
            <div className="credential-exposure">
              <div className="info-row">
                <span className="info-label">Level:</span>
                <span className="info-value">{credentialExposure.level || "N/A"}</span>
              </div>
              {credentialExposure.notes && (
                <div className="info-row">
                  <span className="info-label">Notes:</span>
                  <span className="info-value"><EvidenceText text={credentialExposure.notes} /></span>
                </div>
              )}
            </div>
          </div>
        )}

        {data.host_mutation_status && (
          <div className="report-section">
            <h3>Host Mutation Status</h3>
            <p className="status-text"><EvidenceText text={data.host_mutation_status} /></p>
          </div>
        )}

        {data.migration_status && (
          <div className="report-section">
            <h3>Migration Status</h3>
            <p className="status-text"><EvidenceText text={data.migration_status} /></p>
          </div>
        )}
      </div>
    </div>
  );
}
