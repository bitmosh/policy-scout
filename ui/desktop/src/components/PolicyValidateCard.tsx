// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, PolicyValidateData } from "../types";
import { StatusPill } from "./StatusPill";

interface PolicyValidateCardProps {
  policyValidate: CliJsonResponse<PolicyValidateData> | null;
  loading?: boolean;
  onRunValidate?: () => void;
}

export function PolicyValidateCard({ policyValidate, loading = false, onRunValidate }: PolicyValidateCardProps) {
  const data = policyValidate?.data;
  const issues = data?.issues ?? [];
  const isValid = data?.is_valid;

  return (
    <div className="policy-validate-card">
      <div className="card-header">
        <h2>Policy Validation</h2>
        {onRunValidate && (
          <button className="action-btn" onClick={onRunValidate} disabled={loading}>
            {loading ? "Validating…" : "Re-validate"}
          </button>
        )}
      </div>

      {loading && <p className="status-message">Running policy validation...</p>}

      {!loading && policyValidate?.ok && data && (
        <div className="validate-data">
          <div className="validate-summary">
            <StatusPill
              label="Status"
              tone={isValid ? "success" : "danger"}
              value={isValid ? "Valid" : "Invalid"}
            />
            <div className="info-row">
              <span className="info-label">Rules checked:</span>
              <span className="info-value">{data.rules_checked ?? 0}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Eval cases:</span>
              <span className="info-value">{data.eval_cases_checked ?? 0}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Errors:</span>
              <span className="info-value">{data.error_count ?? 0}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Warnings:</span>
              <span className="info-value">{data.warning_count ?? 0}</span>
            </div>
          </div>

          {issues.length > 0 && (
            <div className="validate-issues">
              <h4>Issues</h4>
              <div className="issues-list">
                {issues.map((issue, index) => (
                  <div key={index} className="issue-item">
                    <StatusPill
                      label=""
                      tone={issue.severity === "error" ? "danger" : "warning"}
                      value={issue.severity.toUpperCase()}
                      className="issue-severity-pill"
                    />
                    <span className="issue-description">{issue.description}</span>
                    {issue.rule_id && issue.rule_id !== "(none)" && (
                      <span className="issue-rule">rule: {issue.rule_id}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {issues.length === 0 && (
            <p className="empty-message">No issues found</p>
          )}
        </div>
      )}

      {!loading && policyValidate && !policyValidate.ok && (
        <p className="empty-message">{policyValidate.error ?? "Could not run policy validation"}</p>
      )}

      {!loading && !policyValidate && (
        <p className="empty-message">Run validation to check policy configuration</p>
      )}
    </div>
  );
}
