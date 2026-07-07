import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { GuidedFaqPrompt, CliJsonResponse, DecisionCheckData, DecisionCheckDecision, RunGateData, RunGateExecutionData } from "../types";

const FAQ_PROMPTS: GuidedFaqPrompt[] = [
  {
    id: "check-vs-run",
    category: "command_safety",
    label: "What is the difference between check and run?",
    description: "Understanding Policy Scout's two main commands",
    explanation: "The `check` command classifies a command without executing it. It returns a decision (ALLOW, REQUIRE_APPROVAL, SANDBOX_FIRST, DENY, DENY_AND_ALERT) along with risk score, category, and reasons. The `run` command executes only ALLOW decisions. Use `check` to understand how Policy Scout would classify a command before you decide whether to run it.",
    safetyNote: "Never use `run` without first understanding the decision."
  },
  {
    id: "npm-sandbox",
    category: "package_installs",
    label: "How do I check whether npm install should be sandboxed?",
    description: "Package install safety classification",
    exampleCommand: "npm install left-pad",
    explanation: "Package installs typically return SANDBOX_FIRST, meaning Policy Scout recommends reviewing the package in a sandbox before installing on the host. The check will show the risk score, category (package_install), capabilities (network.fetch, filesystem.project_write, package.install, lifecycle.execute_possible), and reasons about lifecycle scripts and third-party code.",
    safetyNote: "Package installs may execute arbitrary lifecycle scripts."
  },
  {
    id: "suspicious-package",
    category: "package_installs",
    label: "How do I safely inspect a suspicious package?",
    description: "Package review workflow",
    exampleCommand: "npm install suspicious-package --ignore-scripts=false",
    explanation: "Use `check` to see the classification. If SANDBOX_FIRST, use the sandbox workflow to install in an isolated workspace, inspect lifecycle scripts, review diffs, and then decide whether to migrate to the host. The sandbox result report will show what files changed, what scripts ran, and any credential exposure assessment.",
    safetyNote: "Never install directly from untrusted sources without sandbox review."
  },
  {
    id: "dry-run-cleanup",
    category: "cleanup_dry_run",
    label: "What does dry-run cleanup show?",
    description: "Understanding cleanup preview",
    explanation: "The cleanup dry-run shows what would be deleted without actually deleting anything. It lists planned items (paths and sizes), total items, total bytes, and any items that could not be verified. Always review the dry-run output before running actual cleanup.",
    safetyNote: "Dry-run is safe; actual cleanup is irreversible."
  },
  {
    id: "could-not-verify",
    category: "sweep_findings",
    label: "What does could-not-verify mean?",
    description: "Sweep finding interpretation",
    explanation: "When a sweep reports 'could not verify', it means Policy Scout could not confidently determine whether a file or pattern is safe or risky. This often happens with obfuscated code, minified files, or unusual patterns. Review these items manually before trusting them.",
    safetyNote: "Could-not-verify items require manual review."
  },
  {
    id: "read-report",
    category: "reports_audit",
    label: "How do I read a Scout report?",
    description: "Report structure and interpretation",
    explanation: "Scout reports include a summary, findings (with severity, confidence, category, location, evidence, why it matters, and recommended action), could-not-verify items, credential exposure assessment, and host mutation status. Start with the summary, then review high-severity findings first.",
    safetyNote: "Reports may contain redacted sensitive information."
  },
  {
    id: "why-blocked",
    category: "command_safety",
    label: "Why was this command blocked?",
    description: "Understanding DENY decisions",
    exampleCommand: "rm -rf /",
    explanation: "Commands are blocked (DENY or DENY_AND_ALERT) when they pose unacceptable risk. Common reasons: destructive filesystem mutation, network-fetched script execution (curl | bash), credential-adjacent access (cat ~/.ssh/id_rsa), or other high-risk patterns. The check response will include specific reasons explaining the decision.",
    safetyNote: "Blocked commands should not be executed without careful review."
  },
  {
    id: "suspicious-sweep",
    category: "sweep_findings",
    label: "What should I do after a suspicious sweep finding?",
    description: "Sweep finding response workflow",
    explanation: "After a sweep identifies suspicious patterns: 1) Review the finding details (location, evidence, why it matters). 2) Check the file manually. 3) If it's a false positive, document it. 4) If it's truly suspicious, remove or remediate the file. 5) Re-run the sweep to confirm remediation.",
    safetyNote: "Don't ignore high-severity findings without review."
  },
  {
    id: "credential-rotation",
    category: "credential_hygiene",
    label: "What should I do before rotating credentials?",
    description: "Credential rotation preparation",
    explanation: "Before rotating credentials: 1) Run a sweep to check for exposed credentials in code. 2) Review audit events for credential access. 3) Check Scout reports for credential exposure assessments. 4) Identify all systems using the credential. 5) Plan the rotation to avoid downtime.",
    safetyNote: "Credential rotation requires coordination across systems."
  },
  {
    id: "browser-preview",
    category: "troubleshooting",
    label: "Why does browser preview show Tauri runtime unavailable?",
    description: "Development mode explanation",
    explanation: "The browser preview (`npm run dev`) cannot access Tauri's native invoke APIs, so it cannot load live Policy Scout CLI data. It shows a friendly message indicating this limitation. To see live data, use the native Tauri runtime (`npm run tauri dev`).",
    safetyNote: "Browser preview is for layout testing only."
  },
  {
    id: "approvals-work",
    category: "approvals",
    label: "How do approvals work?",
    description: "Approval system overview",
    explanation: "Approvals are one-time, narrow, auditable permissions for risky commands. When a command returns REQUIRE_APPROVAL, you can request an approval. The approval includes the exact command, current working directory, and expiration. Approved execution only applies if the command still evaluates to REQUIRE_APPROVAL at execution time. Approvals do not bypass DENY or SANDBOX_FIRST.",
    safetyNote: "Approvals are one-time and scoped to specific commands."
  },
  {
    id: "local-first",
    category: "dashboard_navigation",
    label: "What does local-first mean?",
    description: "Local-first architecture",
    explanation: "Policy Scout is designed to be local-first: all data (audit events, reports, approvals, sandbox workspaces) lives on your machine by default. No automatic remote upload. No cloud dependency for core operation. This keeps your data private and under your control.",
    safetyNote: "Local-first means your data stays on your machine."
  },
];

const WHAT_NOW: Record<DecisionCheckDecision, {
  color: string; title: string; steps: string[];
  navHint?: { label: string; view: string };
}> = {
  ALLOW: {
    color: "var(--color-success)", title: "Safe to proceed",
    steps: ["This command is within policy.", "No additional action required."],
  },
  ALLOW_LOGGED: {
    color: "var(--color-success)", title: "Allowed — logged for review",
    steps: [
      "This command is permitted but has been logged for audit.",
      "Check the Audit view if you want to track ALLOW_LOGGED events.",
    ],
    navHint: { label: "Go to Audit", view: "audit" },
  },
  REQUIRE_APPROVAL: {
    color: "var(--color-review)", title: "Approval required before running",
    steps: [
      "Do not run this command until an approval is granted.",
      "Request via CLI: policy-scout approve <command>",
      "Approvals are one-time, scoped to the exact command, and audited.",
    ],
  },
  SANDBOX_FIRST: {
    color: "var(--color-warning)", title: "Test in a sandbox first",
    steps: [
      "Do not install directly on the host.",
      "Use the Sandbox view to run in isolation, inspect lifecycle scripts, then decide.",
      "CLI: policy-scout sandbox install <package>",
    ],
    navHint: { label: "Go to Sandbox", view: "sandbox" },
  },
  DENY: {
    color: "var(--color-danger)", title: "Blocked — do not run",
    steps: [
      "This command is explicitly denied by policy.",
      "Use Policy → Simulate to see which rule matched and why.",
      "If this is a false positive, check Policy for project override options.",
    ],
    navHint: { label: "Policy Simulate", view: "policy" },
  },
  DENY_AND_ALERT: {
    color: "var(--color-danger)", title: "Blocked and flagged",
    steps: [
      "This command is blocked and a high-severity alert has been logged.",
      "Review the Audit log — this event is marked for follow-up.",
      "Do not attempt to work around this block without understanding why it fired.",
    ],
    navHint: { label: "Go to Audit", view: "audit" },
  },
};

function WhatNow({ decision, onGoTo }: {
  decision: DecisionCheckDecision;
  onGoTo?: (view: string) => void;
}) {
  const g = WHAT_NOW[decision];
  if (!g) return null;
  return (
    <div style={{
      marginTop: 16,
      borderLeft: `3px solid ${g.color}`,
      borderRadius: "0 8px 8px 0",
      background: `color-mix(in srgb, ${g.color} 7%, var(--color-panel))`,
      padding: "12px 14px",
    }}>
      <div style={{ fontSize: 12.5, fontWeight: 700, color: g.color, marginBottom: 8 }}>{g.title}</div>
      <ul style={{ margin: 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 4 }}>
        {g.steps.map((s, i) => (
          <li key={i} style={{ fontSize: 12.5, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>{s}</li>
        ))}
      </ul>
      {g.navHint && onGoTo && (
        <button
          onClick={() => onGoTo(g.navHint!.view)}
          style={{
            marginTop: 10, padding: "4px 10px", fontSize: 12, fontWeight: 600,
            background: "transparent", border: `1px solid color-mix(in srgb, ${g.color} 40%, transparent)`,
            borderRadius: 6, color: g.color, cursor: "pointer",
          }}
        >
          {g.navHint.label} →
        </button>
      )}
    </div>
  );
}

export function DecisionCheckCard({ onGoTo }: { onGoTo?: (view: string) => void }) {
  const [commandText, setCommandText] = useState("");
  const [selectedFaq, setSelectedFaq] = useState<GuidedFaqPrompt | null>(null);
  const [checkResult, setCheckResult] = useState<DecisionCheckData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<CliJsonResponse<RunGateData> | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const validateCommandText = (text: string): string | null => {
    if (!text || text.trim() === "") {
      return "Command cannot be empty.";
    }
    if (text.length > 4000) {
      return "Command is too long (max 4000 characters).";
    }
    if (text.includes("\0")) {
      return "Command contains invalid characters.";
    }
    return null;
  };

  const handleFaqClick = (faq: GuidedFaqPrompt) => {
    setSelectedFaq(faq);
    setCheckResult(null);
    setError(null);
    if (faq.exampleCommand) {
      setCommandText(faq.exampleCommand);
    }
  };

  const handleCommandChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCommandText(e.target.value);
    setError(null);
  };

  const handleCheck = async () => {
    const validationError = validateCommandText(commandText);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);
    setCheckResult(null);
    setRunResult(null);
    setRunError(null);

    try {
      const response = await invoke<CliJsonResponse<DecisionCheckData>>("check_command", {
        commandText: commandText,
      });

      if (response.ok && response.data) {
        setCheckResult(response.data);
      } else {
        setError(response.error || "Check failed.");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!checkResult) return;
    setRunLoading(true);
    setRunError(null);
    setRunResult(null);
    try {
      const response = await invoke<CliJsonResponse<RunGateData>>("run_command_through_gate", {
        commandText: checkResult.command,
      });
      setRunResult(response);
    } catch (err) {
      setRunError(String(err));
    } finally {
      setRunLoading(false);
    }
  };

  const isButtonDisabled = loading || !commandText.trim() || !!validateCommandText(commandText);

  const getDecisionClass = (decision: string): string => {
    switch (decision) {
      case "ALLOW":
        return "decision-allow";
      case "REQUIRE_APPROVAL":
        return "decision-approval";
      case "SANDBOX_FIRST":
        return "decision-sandbox";
      case "DENY":
        return "decision-deny";
      case "DENY_AND_ALERT":
        return "decision-deny-alert";
      default:
        return "";
    }
  };

  const getRiskBandClass = (riskBand: string): string => {
    switch (riskBand) {
      case "low":
        return "risk-low";
      case "medium":
        return "risk-medium";
      case "high":
        return "risk-high";
      case "critical":
        return "risk-critical";
      default:
        return "";
    }
  };

  return (
    <div className="card decision-check-card">
      <div className="card-header">
        <h2>Decision Check</h2>
      </div>
      <div className="card-body">
        <div className="check-only-banner">
          <strong>CHECK ONLY — commands are classified, never executed.</strong>
        </div>
        <p className="check-only-helper">
          This panel will use <code>policy-scout check --json</code> only. It will never call <code>run</code>.
        </p>

        <div className="faq-section">
          <h3>Guided FAQ</h3>
          <div className="faq-buttons">
            {FAQ_PROMPTS.map((faq) => (
              <button
                key={faq.id}
                className={`faq-button ${selectedFaq?.id === faq.id ? "active" : ""}`}
                onClick={() => handleFaqClick(faq)}
              >
                {faq.label}
              </button>
            ))}
          </div>
        </div>

        {selectedFaq && (
          <div className="faq-detail">
            <h4>{selectedFaq.label}</h4>
            <p className="faq-description">{selectedFaq.description}</p>
            <div className="faq-explanation">
              <strong>Explanation:</strong>
              <p>{selectedFaq.explanation}</p>
            </div>
            {selectedFaq.safetyNote && (
              <div className="faq-safety-note">
                <strong>Safety Note:</strong> {selectedFaq.safetyNote}
              </div>
            )}
          </div>
        )}

        <div className="command-input-section">
          <label htmlFor="command-text">Command to check:</label>
          <textarea
            id="command-text"
            className="command-textarea"
            value={commandText}
            onChange={handleCommandChange}
            placeholder="Type or paste a command to check..."
            rows={4}
          />
          {error && <p className="validation-error">{error}</p>}
          {selectedFaq?.exampleCommand && commandText === selectedFaq.exampleCommand && (
            <p className="example-warning">
              <strong>Example only — do not run this command without review.</strong>
            </p>
          )}
        </div>

        <div className="check-action-section">
          <button className="check-button" onClick={handleCheck} disabled={isButtonDisabled}>
            {loading ? "Checking..." : "Check command"}
          </button>
          <p className="check-button-helper">This classifies only. The command is not executed.</p>
        </div>

        {checkResult && (
          <div className="check-result-panel">
            <div className="not-executed-marker">
              <strong>NOT EXECUTED</strong>
            </div>
            <div className="result-header">
              <h3>Classification Result</h3>
              {checkResult.request_id && (
                <span className="request-id">ID: {checkResult.request_id}</span>
              )}
            </div>
            <div className="result-section">
              <h4>Original Command</h4>
              <code className="command-display">{checkResult.command}</code>
            </div>
            <div className="result-section">
              <h4>Decision</h4>
              <span className={`decision-badge ${getDecisionClass(checkResult.decision)}`}>
                {checkResult.decision}
              </span>
            </div>
            <div className="result-section">
              <h4>Risk Assessment</h4>
              <div className="risk-row">
                <span className={`risk-badge ${getRiskBandClass(checkResult.risk_band)}`}>
                  {checkResult.risk_band.toUpperCase()}
                </span>
                <span className="risk-score">Score: {checkResult.risk_score}</span>
              </div>
            </div>
            <div className="result-section">
              <h4>Category</h4>
              <span className="category-badge">{checkResult.category}</span>
            </div>
            {checkResult.confidence && (
              <div className="result-section">
                <h4>Confidence</h4>
                <span className="confidence-badge">{(checkResult.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
            <div className="result-section">
              <h4>Capabilities</h4>
              {checkResult.capabilities && checkResult.capabilities.length > 0 ? (
                <div className="capabilities-list">
                  {checkResult.capabilities.map((cap, idx) => (
                    <span key={idx} className="capability-tag">
                      {cap}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="empty-value">None</span>
              )}
            </div>
            <div className="result-section">
              <h4>Reasons</h4>
              {checkResult.reasons && checkResult.reasons.length > 0 ? (
                <ul className="reasons-list">
                  {checkResult.reasons.map((reason, idx) => (
                    <li key={idx}>{reason}</li>
                  ))}
                </ul>
              ) : (
                <span className="empty-value">None</span>
              )}
            </div>
            {checkResult.recommended_next_action && (
              <div className="result-section">
                <h4>Recommended Next Action</h4>
                <p className="recommended-action">{checkResult.recommended_next_action}</p>
              </div>
            )}
            {checkResult.registry_hits && checkResult.registry_hits.length > 0 && (
              <div className="result-section">
                <h4>Registry Hits</h4>
                <ul className="registry-hits-list">
                  {checkResult.registry_hits.map((hit, idx) => (
                    <li key={idx}>
                      <span className="registry-name">{hit.registry_name}</span>
                      {hit.entry_id && <span className="registry-entry">: {hit.entry_id}</span>}
                      {hit.confidence && (
                        <span className="registry-confidence">
                          {" "}
                          ({(hit.confidence * 100).toFixed(0)}%)
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {checkResult.policy_hits && checkResult.policy_hits.length > 0 && (
              <div className="result-section">
                <h4>Policy Hits</h4>
                <ul className="policy-hits-list">
                  {checkResult.policy_hits.map((hit, idx) => (
                    <li key={idx}>{hit}</li>
                  ))}
                </ul>
              </div>
            )}
            <WhatNow decision={checkResult.decision} onGoTo={onGoTo} />

            {(checkResult.decision === "ALLOW" || checkResult.decision === "ALLOW_LOGGED") && (
              <div style={{ marginTop: 16 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "10px 14px",
                  background: "color-mix(in srgb, var(--color-success) 6%, var(--color-panel))",
                  border: "1px solid color-mix(in srgb, var(--color-success) 20%, transparent)",
                  borderRadius: 8,
                }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)", flex: 1 }}>
                    Policy gate: {checkResult.decision}. Run this command through the gate?
                  </span>
                  <button
                    onClick={handleRun}
                    disabled={runLoading}
                    style={{
                      padding: "5px 14px", fontSize: 12, fontWeight: 600,
                      background: runLoading ? "var(--color-elevated)" : "var(--color-success)",
                      color: runLoading ? "var(--color-text-muted)" : "#fff",
                      border: "1px solid var(--color-border)", borderRadius: 6,
                      cursor: runLoading ? "not-allowed" : "pointer", flexShrink: 0,
                    }}
                  >
                    {runLoading ? "Running…" : "Run"}
                  </button>
                </div>

                {runError && (
                  <div style={{ marginTop: 8, fontSize: 12, color: "var(--color-danger)" }}>{runError}</div>
                )}

                {runResult && (
                  <div style={{
                    marginTop: 10, padding: "12px 14px",
                    background: "var(--color-elevated)",
                    border: "1px solid var(--color-border-muted)",
                    borderRadius: 8,
                  }}>
                    {runResult.ok && runResult.data && "execution_id" in runResult.data ? (
                      (() => {
                        const exec = runResult.data as RunGateExecutionData;
                        return (
                          <>
                            <div style={{ display: "flex", gap: 12, fontSize: 11, color: "var(--color-text-muted)", marginBottom: 8, flexWrap: "wrap" }}>
                              <span style={{ fontWeight: 600, color: exec.exit_code === 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                                exit {exec.exit_code ?? "?"}
                              </span>
                              {exec.duration_ms != null && <span>{exec.duration_ms}ms</span>}
                              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10 }}>{exec.execution_id}</span>
                            </div>
                            {exec.stdout && (
                              <pre style={{
                                margin: 0, fontSize: 11, fontFamily: "var(--font-mono)",
                                color: "var(--color-text-secondary)", whiteSpace: "pre-wrap",
                                wordBreak: "break-all", maxHeight: 200, overflowY: "auto",
                              }}>
                                {exec.stdout}
                              </pre>
                            )}
                            {exec.stderr && (
                              <pre style={{
                                margin: "6px 0 0", fontSize: 11, fontFamily: "var(--font-mono)",
                                color: "var(--color-warning)", whiteSpace: "pre-wrap",
                                wordBreak: "break-all", maxHeight: 100, overflowY: "auto",
                              }}>
                                {exec.stderr}
                              </pre>
                            )}
                            {!exec.stdout && !exec.stderr && (
                              <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>No output.</span>
                            )}
                          </>
                        );
                      })()
                    ) : (
                      <div style={{ fontSize: 12, color: "var(--color-danger)" }}>
                        {runResult.error ?? "Command was blocked by policy."}
                        {runResult.data && "decision" in runResult.data && (
                          <span style={{ marginLeft: 6, fontWeight: 600 }}>
                            ({(runResult.data as { decision: string }).decision})
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
