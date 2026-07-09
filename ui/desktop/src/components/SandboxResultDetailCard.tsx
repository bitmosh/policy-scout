// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, SandboxResultDetailData, SandboxMigrationData, asArray } from "../types";
import { DetailHeader } from "./DetailHeader";
import { RedactionNotice } from "./RedactionNotice";
import { EvidenceText } from "./EvidenceText";

function FileList({ label, files, color }: { label: string; files: string[]; color?: string }) {
  if (!files.length) return null;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: color ?? "var(--color-text-muted)", marginBottom: 5, fontWeight: 600 }}>{label}</div>
      {files.map((f, i) => (
        <div key={i} className="mono" style={{ fontSize: 11.5, color: "var(--color-text-secondary)", padding: "2px 0" }}>· {f}</div>
      ))}
    </div>
  );
}

function MigrationPanel({ sandboxId, alreadyMigrated, preview, previewLoading, result, resultLoading, onPreview, onMigrate }: {
  sandboxId: string;
  alreadyMigrated: boolean;
  preview: CliJsonResponse<SandboxMigrationData> | null;
  previewLoading: boolean;
  result: CliJsonResponse<SandboxMigrationData> | null;
  resultLoading: boolean;
  onPreview: (id: string) => void;
  onMigrate: (id: string) => void;
}) {
  const previewData = preview?.data;
  const resultData = result?.data;
  const anyLoading = previewLoading || resultLoading;

  return (
    <div style={{
      marginTop: 20, border: "1px solid var(--color-border-muted)",
      borderRadius: 10, overflow: "hidden",
    }}>
      <div style={{
        padding: "10px 16px", background: "var(--color-elevated)",
        borderBottom: "1px solid var(--color-border-muted)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--color-text-primary)" }}>
          Migrate to project
        </span>
        {alreadyMigrated && (
          <span style={{ fontSize: 11.5, color: "var(--color-success)", fontWeight: 600 }}>Already migrated</span>
        )}
      </div>

      <div style={{ padding: "14px 16px" }}>
        {alreadyMigrated ? (
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--color-text-muted)" }}>
            This sandbox result has already been migrated to the host project.
          </p>
        ) : result ? (
          /* Completed migration result */
          resultData?.blocked || !result.ok ? (
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--color-danger)", marginBottom: 8 }}>Migration blocked</div>
              {(resultData?.block_reasons ?? []).map((r, i) => (
                <div key={i} style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>· {r}</div>
              ))}
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--color-success)", marginBottom: 10 }}>Migration complete</div>
              <FileList label="Files migrated" files={resultData?.files_migrated ?? []} color="var(--color-success)" />
              <FileList label="Backups created" files={resultData?.backups_created ?? []} />
              <FileList label="Files skipped" files={resultData?.files_skipped ?? []} />
              {resultData?.migration_id && (
                <div className="mono" style={{ fontSize: 10.5, color: "var(--color-text-muted)", marginTop: 8 }}>{resultData.migration_id}</div>
              )}
            </div>
          )
        ) : preview ? (
          /* Dry-run plan — show confirm step */
          previewData?.blocked || !preview.ok ? (
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--color-danger)", marginBottom: 8 }}>Migration blocked</div>
              {(previewData?.block_reasons ?? []).map((r, i) => (
                <div key={i} style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>· {r}</div>
              ))}
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 12.5, color: "var(--color-text-muted)", marginBottom: 12 }}>
                Preview — no files have been changed yet.
              </div>
              <FileList label="Files to migrate" files={previewData?.files_planned ?? []} color="var(--color-info)" />
              <FileList label="Files to skip" files={previewData?.files_skipped ?? []} />
              {(previewData?.files_planned?.length ?? 0) === 0 && (
                <div style={{ fontSize: 12.5, color: "var(--color-text-muted)", marginBottom: 12 }}>
                  No files to migrate.
                </div>
              )}
              <button
                onClick={() => onMigrate(sandboxId)}
                disabled={anyLoading || (previewData?.files_planned?.length ?? 0) === 0}
                style={{
                  marginTop: 4, padding: "6px 16px", fontSize: 12.5, fontWeight: 600,
                  background: "var(--color-success)", border: "none", borderRadius: 7,
                  color: "#fff", cursor: "pointer",
                  opacity: (anyLoading || (previewData?.files_planned?.length ?? 0) === 0) ? 0.45 : 1,
                }}
              >
                {resultLoading ? "Migrating…" : "Confirm & migrate"}
              </button>
            </div>
          )
        ) : (
          /* Initial state */
          <div>
            <p style={{ margin: "0 0 12px", fontSize: 12.5, color: "var(--color-text-muted)" }}>
              Apply the reviewed lockfile changes from this sandbox run to your host project.
              No files are changed until you confirm.
            </p>
            <button
              onClick={() => onPreview(sandboxId)}
              disabled={anyLoading}
              style={{
                padding: "6px 16px", fontSize: 12.5, fontWeight: 600,
                background: "var(--color-elevated)", border: "1px solid var(--color-border-muted)",
                borderRadius: 7, color: "var(--color-text-primary)", cursor: "pointer",
                opacity: anyLoading ? 0.5 : 1,
              }}
            >
              {previewLoading ? "Checking…" : "Preview migration"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface SandboxResultDetailCardProps {
  sandboxResultDetail: CliJsonResponse<SandboxResultDetailData> | null;
  loading: boolean;
  selectedId: string;
  onClose: () => void;
  migrationPreview: CliJsonResponse<SandboxMigrationData> | null;
  migrationPreviewLoading: boolean;
  migrationResult: CliJsonResponse<SandboxMigrationData> | null;
  migrationLoading: boolean;
  onMigrateDryRun: (sandboxId: string) => void;
  onMigrate: (sandboxId: string) => void;
}

export function SandboxResultDetailCard({
  sandboxResultDetail, loading, selectedId, onClose,
  migrationPreview, migrationPreviewLoading, migrationResult, migrationLoading,
  onMigrateDryRun, onMigrate,
}: SandboxResultDetailCardProps) {
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

        {data.sandbox_id && (
          <MigrationPanel
            sandboxId={data.sandbox_id}
            alreadyMigrated={data.migration_status === "completed"}
            preview={migrationPreview}
            previewLoading={migrationPreviewLoading}
            result={migrationResult}
            resultLoading={migrationLoading}
            onPreview={onMigrateDryRun}
            onMigrate={onMigrate}
          />
        )}
      </div>
    </div>
  );
}
