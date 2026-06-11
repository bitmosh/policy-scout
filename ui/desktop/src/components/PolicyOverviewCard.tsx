import { CliJsonResponse, PolicyOverviewData } from "../types";
import { StatusPill, StatusTone } from "./StatusPill";

interface PolicyOverviewCardProps {
  policyOverview: CliJsonResponse<PolicyOverviewData> | null;
  loading?: boolean;
}

const DECISION_TONE: Record<string, StatusTone> = {
  ALLOW: "success",
  ALLOW_LOGGED: "success",
  REQUIRE_APPROVAL: "warning",
  SANDBOX_FIRST: "warning",
  DENY: "danger",
  DENY_AND_ALERT: "danger",
};

export function PolicyOverviewCard({ policyOverview, loading = false }: PolicyOverviewCardProps) {
  const data = policyOverview?.data;
  const rules = data?.rules ?? [];

  return (
    <div className="policy-overview-card">
      <div className="card-header">
        <h2>Policy Overview</h2>
      </div>

      {loading && <p className="status-message">Loading policy overview...</p>}

      {!loading && policyOverview?.ok && data && (
        <div className="policy-data">
          <div className="info-row">
            <span className="info-label">Registry Version:</span>
            <span className="info-value">{data.registry_version ?? "N/A"}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Override Active:</span>
            <span className="info-value">{data.override_active ? "Yes" : "No"}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Rules:</span>
            <span className="info-value">{rules.length}</span>
          </div>

          {rules.length > 0 && (
            <div className="policy-rules">
              <h4>Active Rules</h4>
              <div className="rules-list">
                {rules.map((rule) => (
                  <div key={rule.id} className="rule-row">
                    <StatusPill
                      label=""
                      tone={DECISION_TONE[rule.decision] ?? "neutral"}
                      value={rule.decision}
                      className="rule-decision-pill"
                    />
                    <span className="rule-id">{rule.id}</span>
                    <span className="rule-priority">p{rule.priority}</span>
                    {rule.source && rule.source !== "registry" && (
                      <span className="rule-source">{rule.source}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && policyOverview && !policyOverview.ok && (
        <p className="empty-message">{policyOverview.error ?? "Could not load policy overview"}</p>
      )}

      {!loading && !policyOverview && (
        <p className="empty-message">Policy overview not loaded</p>
      )}
    </div>
  );
}
