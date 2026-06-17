import { useEffect } from "react";
import { IcoX } from "./Icons";

interface HelpDrawerProps {
  open: boolean;
  onClose: () => void;
}

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: "inline-block", padding: "1px 7px", borderRadius: 4,
      fontSize: 11, fontWeight: 700, letterSpacing: "0.05em",
      background: color + "22", color, border: `1px solid ${color}44`,
      fontFamily: "var(--font-mono)",
    }}>{label}</span>
  );
}

function DecisionRow({ label, color, desc }: { label: string; color: string; desc: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 8 }}>
      <Chip label={label} color={color} />
      <span style={{ fontSize: 12.5, color: "var(--color-text-secondary)" }}>{desc}</span>
    </div>
  );
}

function CatRow({ cat, desc }: { cat: string; desc: string }) {
  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 5 }}>
      <span style={{
        fontFamily: "var(--font-mono)", color: "var(--color-info)",
        fontSize: 11, flex: "0 0 140px", paddingTop: 1,
      }}>{cat}</span>
      <span style={{ color: "var(--color-text-secondary)", fontSize: 12.5 }}>{desc}</span>
    </div>
  );
}

function Section({ title, children, defaultOpen = false }: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen}>
      <summary className="help-section-summary">
        <span>{title}</span>
        <span className="help-chevron">›</span>
      </summary>
      <div className="help-section-body">{children}</div>
    </details>
  );
}

export function HelpDrawer({ open, onClose }: HelpDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 50,
          background: "rgba(0,0,0,0.45)", backdropFilter: "blur(2px)",
        }}
      />
      <div style={{
        position: "fixed", top: 0, right: 0, bottom: 0, zIndex: 51,
        width: 420, background: "var(--color-panel)",
        borderLeft: "1px solid var(--color-border-muted)",
        display: "flex", flexDirection: "column",
        boxShadow: "-24px 0 64px rgba(0,0,0,0.5)",
      }}>
        <div style={{
          padding: "16px 20px", borderBottom: "1px solid var(--color-border-muted)",
          display: "flex", alignItems: "center", justifyContent: "space-between", flex: "none",
        }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--color-text-primary)" }}>
              Policy Scout Guide
            </div>
            <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 2, letterSpacing: "0.01em" }}>
              Key concepts · Quick reference
            </div>
          </div>
          <button className="iconbtn t focusable" onClick={onClose} aria-label="Close guide">
            <IcoX />
          </button>
        </div>

        <div className="scrollv" style={{ flex: 1, padding: "4px 20px 28px", overflowY: "auto" }}>

          <Section title="What is Policy Scout?" defaultOpen>
            <p style={{ margin: "0 0 8px" }}>
              Policy Scout evaluates AI agent commands against policy rules before they run — deciding whether to allow, block, warn, or audit each one. It logs a permanent record of all evaluations.
            </p>
            <p style={{ margin: 0 }}>
              Everything runs locally. No data leaves your machine. Rules are stored on disk and can be overridden per-project.
            </p>
          </Section>

          <Section title="Decisions" defaultOpen>
            <DecisionRow label="ALLOW" color="var(--color-success)" desc="Permitted by policy. Safe to proceed." />
            <DecisionRow label="BLOCK" color="var(--color-danger)" desc="Explicitly denied. Don't run without reviewing why." />
            <DecisionRow label="WARN" color="var(--color-warning)" desc="Risky but not blocked. Review before proceeding." />
            <DecisionRow label="AUDIT" color="var(--color-audit)" desc="Logged and allowed — flagged for later review." />
            <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--color-text-muted)" }}>
              Use Policy → Simulate to see exactly which rule triggered a decision.
            </p>
          </Section>

          <Section title="Risk Bands">
            <DecisionRow label="MINIMAL" color="var(--color-success)" desc="Routine operations. Low impact." />
            <DecisionRow label="LOW" color="#7EC8E3" desc="Some file or process access. Generally safe." />
            <DecisionRow label="MEDIUM" color="var(--color-warning)" desc="Network access or significant file operations." />
            <DecisionRow label="HIGH" color="var(--color-review)" desc="Sensitive data or system modifications — review carefully." />
            <DecisionRow label="CRITICAL" color="var(--color-danger)" desc="Destructive or highly privileged — proceed only if intentional." />
          </Section>

          <Section title="Categories">
            <p style={{ margin: "0 0 10px", fontSize: 12.5, color: "var(--color-text-secondary)" }}>
              Each command is tagged with the types of access it requires:
            </p>
            <CatRow cat="file_system"        desc="Reading, writing, or deleting files" />
            <CatRow cat="network"            desc="HTTP requests and network connections" />
            <CatRow cat="process"            desc="Spawning subprocesses or shells" />
            <CatRow cat="execution"          desc="Running scripts or binaries" />
            <CatRow cat="system"             desc="System-level operations" />
            <CatRow cat="data"               desc="Accessing databases or structured data" />
            <CatRow cat="crypto"             desc="Cryptographic operations" />
            <CatRow cat="package_management" desc="Installing or managing packages" />
          </Section>

          <Section title="Policy Simulate">
            <p style={{ margin: "0 0 8px" }}>
              Enter any command in <strong style={{ color: "var(--color-text-primary)" }}>Policy → Simulate</strong> to preview how policy evaluates it — without running the command.
            </p>
            <p style={{ margin: "0 0 6px" }}>The result shows:</p>
            <ul style={{ margin: "0 0 8px", paddingLeft: 16, color: "var(--color-text-secondary)" }}>
              <li>Which rule matched and why</li>
              <li>The full rule trace (every rule checked in order)</li>
              <li>Whether a project override is active</li>
            </ul>
            <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
              Decisive rules are marked ▶. Matched rules are marked ✓. Unmatched rules are dimmed.
            </p>
          </Section>

          <Section title="Audit Log">
            <p style={{ margin: "0 0 8px" }}>
              Every evaluation is logged with its decision, risk score, matched rule, and timestamp. The <strong style={{ color: "var(--color-text-primary)" }}>Audit</strong> view lets you filter and inspect the full history.
            </p>
            <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
              Filter by event type to focus on BLOCK or WARN events and see what was flagged.
            </p>
          </Section>

          <Section title="Sweeps">
            <p style={{ margin: "0 0 8px" }}>
              Sweeps scan recent commands for risky patterns — things that may have slipped through or accumulated over time.
            </p>
            <ul style={{ margin: "0 0 8px", paddingLeft: 16, color: "var(--color-text-secondary)" }}>
              <li><strong style={{ color: "var(--color-text-primary)" }}>Quick sweep</strong> — fast scan of recent activity</li>
              <li><strong style={{ color: "var(--color-text-primary)" }}>Project sweep</strong> — deeper scan of the current project directory</li>
            </ul>
            <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
              Run sweeps regularly or after a long AI agent session.
            </p>
          </Section>

          <Section title="Project Policy Overrides">
            <p style={{ margin: "0 0 8px" }}>
              Place a{" "}
              <code style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-info)" }}>
                .policy-scout.yaml
              </code>{" "}
              file in any project directory to override global rules for that project.
            </p>
            <p style={{ margin: "0 0 8px" }}>
              <strong style={{ color: "var(--color-text-primary)" }}>Policy → Validate</strong> checks overrides for syntax and conflicts.{" "}
              <strong style={{ color: "var(--color-text-primary)" }}>Policy → Simulate</strong> shows whether an override is active for a given command.
            </p>
            <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
              Overrides are scoped to the directory where the file lives.
            </p>
          </Section>

          <Section title="Data Cleanup">
            <p style={{ margin: "0 0 8px" }}>
              <strong style={{ color: "var(--color-text-primary)" }}>System → Data Cleanup</strong> shows what can be safely deleted: demo data, sandbox workspaces, and sandbox results.
            </p>
            <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
              Always run a dry-run first to see exactly what will be removed. Deletions are permanent and require a two-click confirmation.
            </p>
          </Section>

          <Section title="CLI Quick Reference">
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--color-info)",
              background: "var(--color-elevated)", borderRadius: 8, padding: "10px 14px",
              marginBottom: 8, lineHeight: 2,
            }}>
              <div>policy-scout check &lt;command&gt;</div>
              <div>policy-scout simulate &lt;command&gt;</div>
              <div>policy-scout sweep</div>
              <div>policy-scout policy validate</div>
              <div>policy-scout policy list-rules</div>
              <div>policy-scout audit list</div>
              <div>policy-scout data status</div>
              <div>policy-scout data cleanup --target demo</div>
            </div>
            <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
              Add{" "}
              <code style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>--json</code>{" "}
              to any command for machine-readable output.
            </p>
          </Section>

        </div>
      </div>
    </>
  );
}
