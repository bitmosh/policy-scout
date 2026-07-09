// SPDX-License-Identifier: Apache-2.0
import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { BrandMark } from "./BrandMark";
import {
  IcoOverview, IcoCheck, IcoReports, IcoAudit, IcoSweeps,
  IcoSandbox, IcoSystem, IcoRefresh, IcoLock, IcoPalette, IcoCheck2, IcoPolicy, IcoTerminal, IcoHelp, IcoApprovals, IcoScan,
} from "./Icons";
import { THEMES, type ThemeId } from "../themes";

// Padding-based centering: 7px pad + 18px svg = 32px total.
// Avoids flexbox/grid UA-stylesheet conflicts in WebKitGTK.
const IBTN: React.CSSProperties = {
  display: "inline-block",
  padding: 7,
  lineHeight: 0,
  border: "1px solid transparent",
  borderRadius: 6,
  background: "transparent",
  color: "var(--color-text-muted)",
  cursor: "pointer",
  flexShrink: 0,
  transition: "background-color .12s, color .12s, border-color .12s",
};
const IBTN_HOVER: React.CSSProperties = {
  background: "var(--color-elevated)",
  color: "var(--color-text-secondary)",
  borderColor: "var(--color-border-muted)",
};

function IconBtn({ label, onClick, children, style }: {
  label: string;
  onClick?: () => void;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  const [hov, setHov] = useState(false);
  return (
    <button
      aria-label={label}
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{ ...IBTN, ...(hov ? IBTN_HOVER : {}), ...style }}
    >
      {children}
    </button>
  );
}

export type ViewId = "overview" | "check" | "reports" | "audit" | "approvals" | "sweeps" | "scan" | "sandbox" | "system" | "policy";

type NavEntry = { id: ViewId; label: string; Icon: () => React.ReactElement };

export const NAV: NavEntry[] = [
  { id: "overview",   label: "Overview",   Icon: IcoOverview },
  { id: "check",      label: "Check",      Icon: IcoCheck },
  { id: "reports",    label: "Reports",    Icon: IcoReports },
  { id: "audit",      label: "Audit",      Icon: IcoAudit },
  { id: "approvals",  label: "Approvals",  Icon: IcoApprovals },
  { id: "sweeps",     label: "Sweeps",     Icon: IcoSweeps },
  { id: "scan",       label: "Scan",       Icon: IcoScan },
  { id: "sandbox",    label: "Sandbox",    Icon: IcoSandbox },
  { id: "system",     label: "System",     Icon: IcoSystem },
  { id: "policy",     label: "Policy",     Icon: IcoPolicy },
];

function ThemePicker({ theme: cur, texture, setTheme, setTexture }: {
  theme: ThemeId;
  texture: boolean;
  setTheme: (id: ThemeId) => void;
  setTexture: (fn: (v: boolean) => boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const off = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", off, true);
    return () => document.removeEventListener("pointerdown", off, true);
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <IconBtn label="Theme" onClick={() => setOpen(o => !o)}>
        <IcoPalette />
      </IconBtn>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 40, width: 232,
          background: "var(--color-panel)", border: "1px solid var(--color-border-muted)",
          borderRadius: 10, boxShadow: "0 16px 40px rgba(0,0,0,0.45)", padding: 6,
        }}>
          <div className="eyebrow" style={{ padding: "8px 8px" }}>Theme</div>
          {THEMES.map(t => (
            <button key={t.id} className="t focusable" onClick={() => setTheme(t.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10, width: "100%",
                padding: "8px", border: "none",
                background: t.id === cur ? "var(--color-elevated)" : "transparent",
                borderRadius: 7, cursor: "pointer", textAlign: "left",
              }}>
              <span style={{ display: "flex", gap: 3 }}>
                {t.swatch.map((c, i) => (
                  <span key={i} style={{ width: 9, height: 9, borderRadius: "50%", background: c, boxShadow: "0 0 0 1px rgba(128,128,128,0.25)" }} />
                ))}
              </span>
              <span style={{ flex: 1, fontSize: 12.5, color: "var(--color-text-primary)", fontWeight: t.id === cur ? 600 : 500 }}>
                {t.name}
              </span>
              {t.id === cur && <span style={{ color: "var(--color-info)", display: "flex" }}><IcoCheck2 /></span>}
            </button>
          ))}
          <div style={{ height: 1, background: "var(--color-border-muted)", margin: "6px 4px" }} />
          <button className="t focusable" onClick={() => setTexture(v => !v)}
            style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "8px", border: "none", background: "transparent", borderRadius: 7, cursor: "pointer" }}>
            <span style={{ flex: 1, textAlign: "left", fontSize: 12.5, color: "var(--color-text-secondary)" }}>
              Dot-grid texture
            </span>
            <span style={{
              width: 32, height: 18, borderRadius: 999,
              background: texture ? "var(--color-info)" : "var(--color-elevated)",
              border: "1px solid var(--color-border)", position: "relative", display: "block",
            }}>
              <span style={{
                position: "absolute", top: 1, left: texture ? 15 : 1,
                width: 14, height: 14, borderRadius: "50%", background: "#fff",
                transition: "left .15s ease",
              }} />
            </span>
          </button>
        </div>
      )}
    </div>
  );
}

const CLI_CMD = "policy-scout";

function CliLauncher() {
  const [copied, setCopied] = useState(false);
  const [launchErr, setLaunchErr] = useState<string | null>(null);

  useEffect(() => {
    if (!launchErr) return;
    const t = setTimeout(() => setLaunchErr(null), 4000);
    return () => clearTimeout(t);
  }, [launchErr]);

  function handleCopy() {
    navigator.clipboard.writeText(CLI_CMD).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 0,
        border: "1px solid var(--color-border-muted)", borderRadius: 7,
        background: "var(--color-elevated)", overflow: "hidden",
      }}>
        <span className="mono" style={{
          flex: 1, padding: "6px 10px", fontSize: 11.5,
          color: "var(--color-info)", userSelect: "all",
        }}>
          {CLI_CMD}
        </span>
        <button
          onClick={handleCopy}
          className="t focusable"
          title="Copy command"
          style={{
            padding: "6px 9px", border: "none", borderLeft: "1px solid var(--color-border-muted)",
            background: "transparent", cursor: "pointer",
            fontSize: 11, fontWeight: 600,
            color: copied ? "var(--color-success)" : "var(--color-text-muted)",
          }}
        >
          {copied ? "✓" : "⎘"}
        </button>
      </div>
      <button
        className="t focusable"
        onClick={() => invoke("open_terminal")
          .then(() => setLaunchErr(null))
          .catch((e) => setLaunchErr(String(e)))
        }
        style={{
          display: "flex", alignItems: "center", gap: 8, width: "100%",
          padding: "7px 8px", border: "1px solid var(--color-border-muted)",
          borderRadius: 7, background: "transparent", cursor: "pointer",
          color: "var(--color-text-secondary)", fontSize: 12, fontWeight: 500,
        }}
      >
        <IcoTerminal />
        <span>Launch terminal</span>
      </button>
      {launchErr && (
        <div style={{
          fontSize: 11, color: "var(--color-warning)",
          background: "rgba(245,184,75,0.08)", borderRadius: 5,
          padding: "4px 8px", lineHeight: 1.5,
        }}>
          {launchErr.includes("No terminal")
            ? "No terminal found. Set the TERMINAL env var or install xterm."
            : "Launch failed — check your terminal emulator is installed."}
        </div>
      )}
    </div>
  );
}

export function Sidebar({ active, onSelect, cliVersion, healthy, badges }: {
  active: ViewId;
  onSelect: (id: ViewId) => void;
  cliVersion?: string;
  healthy?: boolean;
  badges?: Partial<Record<ViewId, number>>;
}) {

  const pulseColor = healthy === false ? "var(--color-warning)" : "var(--color-success)";
  const statusLabel = healthy === false ? "Check system" : "Healthy";
  const statusColor = healthy === false ? "var(--color-warning)" : "var(--color-success)";

  return (
    <aside style={{
      background: "var(--color-panel)", borderRight: "1px solid var(--color-border-muted)",
      display: "flex", flexDirection: "column", height: "100%",
    }}>
      <div style={{ padding: "18px 16px 16px", borderBottom: "1px solid var(--color-border-muted)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <BrandMark />
          <div style={{ lineHeight: 1.1 }}>
            <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em", color: "var(--color-text-primary)" }}>
              Policy Scout
            </div>
            <div className="mono" style={{ marginTop: 4, fontSize: 9, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
              Local-first · Secure
            </div>
          </div>
        </div>
      </div>

      <nav style={{ padding: "12px 10px", display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map(({ id, label, Icon }) => (
          <button key={id} className={"nav-item t focusable" + (active === id ? " active" : "")}
            aria-current={active === id ? "page" : undefined} onClick={() => onSelect(id)}>
            <Icon /><span>{label}</span>
            {(badges?.[id] ?? 0) > 0 && (
              <span className="nav-badge">{badges![id]}</span>
            )}
          </button>
        ))}
      </nav>

      <div style={{ padding: "8px 10px", borderTop: "1px solid var(--color-border-muted)" }}>
        <CliLauncher />
      </div>
      <div style={{ padding: "10px 18px", borderTop: "1px solid var(--color-border-muted)", display: "flex", alignItems: "center", gap: 9 }}>
        <span className="pulse" style={{ background: pulseColor }} />
        <span className="mono" style={{ fontSize: 11.5, color: "var(--color-text-secondary)", letterSpacing: "0.01em" }}>
          {cliVersion ?? "CLI"}{" "}
          <span style={{ color: "var(--color-text-muted)" }}>·</span>{" "}
          <span style={{ color: statusColor }}>{statusLabel}</span>
        </span>
      </div>
    </aside>
  );
}

export function TopBar({ label, onCheck, onRefresh, onHelp, lockdownActive, theme, texture, setTheme, setTexture }: {
  label: string;
  onCheck: () => void;
  onRefresh: () => void;
  onHelp: () => void;
  lockdownActive?: boolean;
  theme: ThemeId;
  texture: boolean;
  setTheme: (id: ThemeId) => void;
  setTexture: (fn: (v: boolean) => boolean) => void;
}) {
  const [spin, setSpin] = useState(false);

  function handleRefresh() {
    setSpin(true);
    onRefresh();
    setTimeout(() => setSpin(false), 600);
  }

  return (
    <header style={{
      height: 56, flex: "none", background: "var(--color-panel)",
      borderBottom: "1px solid var(--color-border-muted)",
      display: "flex", alignItems: "center", gap: 20, padding: "0 18px",
    }}>
      <div style={{ width: 200, flex: "none", display: "flex", alignItems: "center", gap: 8, fontSize: 13.5 }}>
        <span style={{ color: "var(--color-text-muted)" }}>Scout</span>
        <span style={{ color: "var(--color-border)" }}>/</span>
        <span style={{ color: "var(--color-text-primary)", fontWeight: 600 }}>{label}</span>
      </div>

      <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
        <button className="cmdk t focusable" aria-label="Check a command" onClick={onCheck}>
          <span style={{ color: "var(--color-info)", fontFamily: "var(--font-mono)", fontSize: 14, lineHeight: 1 }}>›</span>
          <span style={{ flex: 1, textAlign: "left", fontFamily: "var(--font-mono)", fontSize: 12.5, letterSpacing: "0.01em" }}>
            scout check &lt;command&gt;
          </span>
          <span className="kbd">⌘K</span>
        </button>
      </div>

      <div style={{ width: 200, flex: "none", display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
        <IconBtn label="Guide" onClick={onHelp}>
          <IcoHelp />
        </IconBtn>
        <ThemePicker theme={theme} texture={texture} setTheme={setTheme} setTexture={setTexture} />
        <IconBtn label="Refresh" onClick={handleRefresh} style={spin ? { animation: "spinonce .6s ease-out" } : undefined}>
          <IcoRefresh />
        </IconBtn>
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, letterSpacing: "0.01em",
          color: lockdownActive ? "var(--color-danger)" : "var(--color-text-muted)",
          fontWeight: lockdownActive ? 700 : 400,
        }}>
          <IcoLock /><span>{lockdownActive ? "LOCKDOWN" : "Redaction on"}</span>
        </span>
      </div>
    </header>
  );
}
