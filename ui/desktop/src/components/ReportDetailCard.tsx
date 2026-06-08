import { CliJsonResponse } from "../types";
import { DetailHeader } from "./DetailHeader";
import { StatusPill, severityToTone } from "./StatusPill";
import { RedactionNotice } from "./RedactionNotice";
import { EvidenceText } from "./EvidenceText";

interface ReportDetailCardProps {
  reportDetail: CliJsonResponse | null;
  loading: boolean;
  onClose: () => void;
}

export function ReportDetailCard({ reportDetail, loading, onClose }: ReportDetailCardProps) {
  const data = reportDetail?.data;
  const reportId = data?.report_id || "N/A";

  if (loading) {
    return (
      <div className="report-detail-card">
        <DetailHeader detailType="Scout Report" selectedId="Loading..." onClose={onClose} />
        <p className="status-message">Loading report...</p>
      </div>
    );
  }

  if (!reportDetail || !reportDetail.ok || !data) {
    return (
      <div className="report-detail-card">
        <DetailHeader detailType="Scout Report" selectedId="N/A" onClose={onClose} />
        <p className="empty-message">No report data available</p>
      </div>
    );
  }

  const findings = data.findings as any[] || [];
  const couldNotVerify = data.could_not_verify as any[] || [];
  const recommendedActions = data.recommended_actions as any[] || [];
  const redactionApplied = data.redaction_applied as boolean || false;
  const credentialExposure = data.credential_exposure_assessment as any || null;
  const findingsCount = data.findings_count as any || null;

  return (
    <div className="report-detail-card">
      <DetailHeader detailType="Scout Report" selectedId={reportId} onClose={onClose} />

      <div className="report-detail-content">
        <RedactionNotice show={redactionApplied} />

        <div className="report-metadata">
          <div className="info-row">
            <span className="info-label">Report ID:</span>
            <span className="info-value">{data.report_id || "N/A"}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Report Type:</span>
            <span className="info-value">{data.report_type || "N/A"}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Title:</span>
            <span className="info-value">{data.title || "N/A"}</span>
          </div>
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

        {data.summary && (
          <div className="report-section">
            <h3>Summary</h3>
            <p className="report-summary"><EvidenceText text={data.summary} /></p>
          </div>
        )}

        {findingsCount && (
          <div className="report-section">
            <h3>Findings Count</h3>
            <div className="findings-count">
              <span className="count-item">Critical: {findingsCount.critical || 0}</span>
              <span className="count-item">High: {findingsCount.high || 0}</span>
              <span className="count-item">Medium: {findingsCount.medium || 0}</span>
              <span className="count-item">Low: {findingsCount.low || 0}</span>
              <span className="count-item">Info: {findingsCount.info || 0}</span>
            </div>
          </div>
        )}

        {findings.length > 0 && (
          <div className="report-section">
            <h3>Findings</h3>
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
                    <span className="finding-category">{finding.category}</span>
                  </div>
                  <div className="finding-title"><EvidenceText text={finding.title} /></div>
                  {finding.location && (
                    <div className="finding-location"><EvidenceText text={finding.location} className="finding-location" /></div>
                  )}
                </div>
              ))}
              {findings.length > 10 && (
                <p className="findings-truncated">... and {findings.length - 10} more findings</p>
              )}
            </div>
          </div>
        )}

        {recommendedActions.length > 0 && (
          <div className="report-section">
            <h3>Recommended Actions</h3>
            <ul className="actions-list">
              {recommendedActions.map((action: any, index: number) => (
                <li key={index} className="action-item"><EvidenceText text={typeof action === "string" ? action : JSON.stringify(action)} /></li>
              ))}
            </ul>
          </div>
        )}

        {couldNotVerify.length > 0 && (
          <div className="report-section">
            <h3>Could Not Verify</h3>
            <ul className="could-not-verify-list">
              {couldNotVerify.map((item: any, index: number) => (
                <li key={index} className="could-not-verify-item"><EvidenceText text={typeof item === "string" ? item : JSON.stringify(item)} /></li>
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

        {data.sweep_id && (
          <div className="report-section">
            <h3>Sweep ID</h3>
            <p className="status-text"><EvidenceText text={data.sweep_id} /></p>
          </div>
        )}

        {data.project_root && (
          <div className="report-section">
            <h3>Project Root</h3>
            <p className="status-text"><EvidenceText text={data.project_root} /></p>
          </div>
        )}
      </div>
    </div>
  );
}
