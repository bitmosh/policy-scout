// SPDX-License-Identifier: Apache-2.0
import { useState, useRef } from "react";
import { CliJsonResponse, SandboxLaunchResultData } from "../types";

function SandboxResultPanel({ result }: { result: CliJsonResponse<SandboxLaunchResultData> }) {
  const d = result.data;
  const success = result.ok && d?.exit_code === 0;
  const durationSec = d?.duration_ms ? (d.duration_ms / 1000).toFixed(1) : "—";
  const scriptCount = d?.lifecycle_scripts_found?.length ?? 0;
  const findingCount = d?.findings?.length ?? 0;

  const statusColor = success ? "var(--color-success)" : "var(--color-danger)";
  const statusLabel = success ? "Install succeeded" : `Install failed (exit ${d?.exit_code ?? "?"})`;

  return (
    <div style={{
      background: "var(--color-panel)", border: `1px solid color-mix(in srgb, ${statusColor} 30%, var(--color-border-muted))`,
      borderRadius: 10, overflow: "hidden",
    }}>
      {/* status header */}
      <div style={{
        padding: "12px 16px", borderBottom: "1px solid var(--color-border-muted)",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor, flex: "none" }} />
        <span style={{ fontSize: 13, fontWeight: 700, color: statusColor }}>{statusLabel}</span>
        <span style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginLeft: "auto" }}>{durationSec}s</span>
      </div>

      {!result.ok && result.error && (
        <div style={{ padding: "10px 16px", fontSize: 12.5, color: "var(--color-danger)", borderBottom: "1px solid var(--color-border-muted)" }}>
          {result.error}
        </div>
      )}

      {d && (
        <>
          {/* meta grid */}
          <div style={{
            padding: "12px 16px", display: "grid", gridTemplateColumns: "repeat(2, 1fr)",
            gap: "10px 20px", borderBottom: "1px solid var(--color-border-muted)",
          }}>
            {[
              ["Package manager", d.package_manager],
              ["Manifest changed", d.manifest_changed ? "Yes" : "No"],
              ["Lockfile changed", d.lockfile_changed ? "Yes" : "No"],
              ["Lifecycle scripts", scriptCount === 0 ? "None found" : `${scriptCount} found`],
              ["Findings", findingCount === 0 ? "None" : String(findingCount)],
              ["Migration available", d.migration_available ? "Yes" : "No"],
            ].map(([label, value]) => (
              <div key={label}>
                <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-text-muted)", marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 12.5, color: "var(--color-text-primary)", fontWeight: 500 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* lifecycle scripts */}
          {scriptCount > 0 && (
            <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--color-border-muted)" }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-warning)", marginBottom: 8, fontWeight: 600 }}>
                Lifecycle scripts detected
              </div>
              {d.lifecycle_scripts_found.map((s, i) => (
                <div key={i} style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)", fontWeight: 600 }}>
                    {s.package_name} — {s.script_name}
                  </div>
                  <pre style={{
                    fontSize: 11, color: "var(--color-text-muted)", margin: "4px 0 0",
                    background: "var(--color-elevated)", borderRadius: 5, padding: "5px 8px",
                    whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 100, overflow: "auto",
                    fontFamily: "var(--font-mono)",
                  }}>
                    {s.script_content}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {/* findings */}
          {findingCount > 0 && (
            <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--color-border-muted)" }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-danger)", marginBottom: 8, fontWeight: 600 }}>
                Findings
              </div>
              {d.findings.map((f, i) => (
                <div key={i} style={{ fontSize: 12.5, color: "var(--color-text-secondary)", marginBottom: 4 }}>
                  [{f.severity ?? "?"}] {f.title ?? f.category ?? "Finding"}
                </div>
              ))}
            </div>
          )}

          {/* stdout preview */}
          {d.stdout && (
            <div style={{ padding: "10px 16px" }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-text-muted)", marginBottom: 6 }}>Output</div>
              <pre style={{
                fontSize: 11, color: "var(--color-text-secondary)", margin: 0,
                background: "var(--color-elevated)", borderRadius: 5, padding: "7px 10px",
                whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 140, overflow: "auto",
                fontFamily: "var(--font-mono)",
              }}>
                {d.stdout}
              </pre>
            </div>
          )}

          {d.migration_available && (
            <div style={{
              padding: "10px 16px", borderTop: "1px solid var(--color-border-muted)",
              fontSize: 12.5, color: "var(--color-info)",
              background: "color-mix(in srgb, var(--color-info) 6%, var(--color-panel))",
            }}>
              Migration ready — run <code className="mono" style={{ fontSize: 11 }}>policy-scout migrate apply</code> to apply to host project.
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface SandboxLaunchCardProps {
  launchResult: CliJsonResponse<SandboxLaunchResultData> | null;
  launchLoading: boolean;
  onLaunch: (cmd: string) => void;
}

export function SandboxLaunchCard({ launchResult, launchLoading, onLaunch }: SandboxLaunchCardProps) {
  const [cmd, setCmd] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: { preventDefault(): void }) {
    e.preventDefault();
    const trimmed = cmd.trim();
    if (!trimmed || launchLoading) return;
    onLaunch(trimmed);
  }

  return (
    <div style={{
      background: "var(--color-panel)", border: "1px solid var(--color-border-muted)",
      borderRadius: 12, overflow: "hidden", marginBottom: 20,
    }}>
      <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--color-border-muted)" }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: "var(--color-text-primary)", marginBottom: 3 }}>
          Sandbox Install
        </div>
        <div style={{ fontSize: 12.5, color: "var(--color-text-muted)" }}>
          Run a package install in an isolated environment — no changes to your host project.
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ padding: "14px 18px", display: "flex", gap: 8 }}>
        <input
          ref={inputRef}
          type="text"
          value={cmd}
          onChange={e => setCmd(e.target.value)}
          placeholder="npm install lodash"
          disabled={launchLoading}
          className="mono focusable"
          style={{
            flex: 1, padding: "8px 12px", fontSize: 13,
            background: "var(--color-elevated)", border: "1px solid var(--color-border-muted)",
            borderRadius: 7, color: "var(--color-text-primary)", outline: "none",
            fontFamily: "var(--font-mono)", opacity: launchLoading ? 0.5 : 1,
          }}
        />
        <button
          type="submit"
          disabled={!cmd.trim() || launchLoading}
          style={{
            padding: "8px 18px", fontSize: 13, fontWeight: 600,
            background: "var(--color-info)", border: "none", borderRadius: 7,
            color: "#fff", cursor: (!cmd.trim() || launchLoading) ? "default" : "pointer",
            opacity: (!cmd.trim() || launchLoading) ? 0.5 : 1,
          }}
        >
          Run
        </button>
      </form>

      {launchLoading && (
        <div style={{
          padding: "10px 18px 14px", display: "flex", alignItems: "center", gap: 10,
          fontSize: 12.5, color: "var(--color-text-muted)", borderTop: "1px solid var(--color-border-muted)",
        }}>
          <span style={{ animation: "spinonce 1s linear infinite", display: "inline-block", opacity: 0.7 }}>⟳</span>
          Running in sandbox — this may take a minute…
        </div>
      )}

      {!launchLoading && launchResult && (
        <div style={{ padding: "0 18px 18px" }}>
          <SandboxResultPanel result={launchResult} />
        </div>
      )}
    </div>
  );
}
