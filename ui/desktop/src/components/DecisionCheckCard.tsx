import { useState } from "react";
import { GuidedFaqPrompt } from "../types";

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

export function DecisionCheckCard() {
  const [commandText, setCommandText] = useState("");
  const [selectedFaq, setSelectedFaq] = useState<GuidedFaqPrompt | null>(null);

  const handleFaqClick = (faq: GuidedFaqPrompt) => {
    setSelectedFaq(faq);
    if (faq.exampleCommand) {
      setCommandText(faq.exampleCommand);
    }
  };

  const handleCommandChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCommandText(e.target.value);
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
          {selectedFaq?.exampleCommand && commandText === selectedFaq.exampleCommand && (
            <p className="example-warning">
              <strong>Example only — do not run this command without review.</strong>
            </p>
          )}
        </div>

        <div className="check-action-section">
          <button className="check-button" disabled>
            Check command (coming next)
          </button>
        </div>
      </div>
    </div>
  );
}
