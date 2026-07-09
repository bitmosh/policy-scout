// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { CliJsonResponse, PolicySimulateData, RuleTrace } from "../types";
import { Chip } from "./Chip";

const DECISION_COLOR: Record<string, string> = {
  ALLOW:            "var(--color-success)",
  ALLOW_LOGGED:     "var(--color-success)",
  REQUIRE_APPROVAL: "var(--color-warning)",
  SANDBOX_FIRST:    "var(--color-warning)",
  DENY:             "var(--color-danger)",
  DENY_AND_ALERT:   "var(--color-danger)",
};

function validateCmd(text: string): string | null {
  if (!text.trim()) return "Command cannot be empty.";
  if (text.length > 4000) return "Command too long (max 4000 characters).";
  if (text.includes("\0")) return "Command contains invalid characters.";
  return null;
}

function RuleRow({ trace }: { trace: RuleTrace }) {
  const color = trace.decisive
    ? (DECISION_COLOR[trace.decision ?? ""] ?? "var(--color-text-primary)")
    : trace.matched
      ? "var(--color-text-secondary)"
      : "var(--color-text-muted)";

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "18px 1fr auto",
      gap: "0 10px",
      alignItems: "start",
      padding: "6px 0",
      borderBottom: "1px solid var(--color-border-muted)",
      opacity: trace.matched || trace.decisive ? 1 : 0.45,
    }}>
      <span style={{ fontSize: 10, color, paddingTop: 2, fontFamily: "var(--font-mono)" }}>
        {trace.decisive ? "▶" : trace.matched ? "✓" : "–"}
      </span>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: trace.decisive ? 600 : 400, color, fontFamily: "var(--font-mono)" }}>
            {trace.rule_id}
          </span>
          <span style={{ fontSize: 10, color: "var(--color-text-muted)" }}>p{trace.priority}</span>
          {trace.source && trace.source !== "registry" && (
            <Chip tone="var(--color-info)" size={9}>{trace.source}</Chip>
          )}
          {trace.decisive && trace.decision && (
            <Chip tone={DECISION_COLOR[trace.decision] ?? "var(--color-text-muted)"} size={9}>
              {trace.decision}
            </Chip>
          )}
        </div>
        {trace.reasons.length > 0 && (
          <div style={{ marginTop: 3 }}>
            {trace.reasons.map((r, i) => (
              <div key={i} style={{ fontSize: 11, color: "var(--color-text-muted)", lineHeight: 1.4 }}>
                {r}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SimulateResult({ data }: { data: PolicySimulateData }) {
  const decisionColor = DECISION_COLOR[data.decision] ?? "var(--color-text-primary)";
  const decisive = data.rule_traces.find(t => t.decisive);
  const matched = data.rule_traces.filter(t => t.matched && !t.decisive);
  const unmatched = data.rule_traces.filter(t => !t.matched);

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
        <span style={{
          fontSize: 15, fontWeight: 700, color: decisionColor,
          fontFamily: "var(--font-mono)", letterSpacing: "0.02em",
        }}>
          {data.decision}
        </span>
        <Chip tone="var(--color-text-muted)" size={10}>risk {data.risk_score}/10</Chip>
        <Chip tone="var(--color-text-muted)" size={10}>{data.risk_band}</Chip>
        {data.matched_rule && (
          <Chip tone={decisionColor} size={10}>matched: {data.matched_rule}</Chip>
        )}
      </div>

      {(data.categories.length > 0 || data.capabilities.length > 0) && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
          {data.categories.map(c => <Chip key={c} tone="var(--color-audit)" size={9}>{c}</Chip>)}
          {data.capabilities.map(c => <Chip key={c} tone="var(--color-info)" size={9}>{c}</Chip>)}
        </div>
      )}

      {data.project_override_loaded && (
        <div style={{ fontSize: 11, color: "var(--color-warning)", marginBottom: 12 }}>
          Project override loaded{data.project_override_path ? ` from ${data.project_override_path}` : ""}
        </div>
      )}

      <div className="eyebrow" style={{ marginBottom: 8 }}>
        Rule trace — {data.total_rules_checked} rule{data.total_rules_checked !== 1 ? "s" : ""} checked
      </div>

      <div>
        {decisive && <RuleRow key={decisive.rule_id} trace={decisive} />}
        {matched.map(t => <RuleRow key={t.rule_id} trace={t} />)}
        {unmatched.map(t => <RuleRow key={t.rule_id} trace={t} />)}
      </div>
    </div>
  );
}

export function PolicySimulateCard() {
  const [commandText, setCommandText] = useState("");
  const [result, setResult] = useState<PolicySimulateData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = async () => {
    const err = validateCmd(commandText);
    if (err) { setError(err); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await invoke<CliJsonResponse<PolicySimulateData>>("run_policy_simulate", { commandText });
      if (resp.ok && resp.data) {
        setResult(resp.data);
      } else {
        setError(resp.error ?? "Simulation failed.");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSimulate();
  };

  const isDisabled = loading || !commandText.trim() || !!validateCmd(commandText);

  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Policy Simulate</div>
      <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 16, lineHeight: 1.5 }}>
        Trace every policy rule against a command — see which matched, which was decisive, and why.
      </div>

      <textarea
        value={commandText}
        onChange={e => { setCommandText(e.target.value); setError(null); }}
        onKeyDown={handleKey}
        placeholder="e.g. npm install lodash"
        rows={2}
        style={{
          width: "100%", boxSizing: "border-box",
          background: "var(--color-elevated)", border: "1px solid var(--color-border)",
          borderRadius: 6, padding: "9px 12px",
          color: "var(--color-text-primary)", fontSize: 13,
          fontFamily: "var(--font-mono)", resize: "vertical",
          outline: "none",
        }}
      />

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
        <button
          onClick={handleSimulate}
          disabled={isDisabled}
          style={{
            padding: "7px 18px", fontSize: 13, fontWeight: 600,
            background: isDisabled ? "var(--color-elevated)" : "var(--color-info)",
            color: isDisabled ? "var(--color-text-muted)" : "#fff",
            border: "1px solid var(--color-border)", borderRadius: 6,
            cursor: isDisabled ? "not-allowed" : "pointer",
            transition: "background 0.12s",
          }}
        >
          {loading ? "Simulating…" : "Simulate"}
        </button>
        <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>⌘↵ to run</span>
      </div>

      {error && (
        <div style={{ marginTop: 12, fontSize: 12, color: "var(--color-danger)" }}>{error}</div>
      )}

      {result && <SimulateResult data={result} />}
    </div>
  );
}
