import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { CliJsonResponse, SecretScanData, InjectionScanData } from "../types";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--color-danger)",
  high:     "var(--color-warning)",
  medium:   "var(--color-info)",
  low:      "var(--color-text-muted)",
};

function RunBtn({ loading, hasResult, onRun }: { loading: boolean; hasResult: boolean; onRun: () => void }) {
  return (
    <button
      onClick={onRun}
      disabled={loading}
      style={{
        padding: "6px 14px", fontSize: 12, fontWeight: 600,
        background: loading ? "var(--color-elevated)" : "var(--color-info)",
        color: loading ? "var(--color-text-muted)" : "#fff",
        border: "1px solid var(--color-border)", borderRadius: 6,
        cursor: loading ? "not-allowed" : "pointer", flexShrink: 0,
      }}
    >
      {loading ? "Scanning…" : hasResult ? "Re-scan" : "Scan"}
    </button>
  );
}

function SecretFindingRow({ f }: { f: { secret_type: string; service: string; severity: string; source: string; line: number; redacted_value: string; guidance: string } }) {
  const color = SEVERITY_COLOR[f.severity] ?? "var(--color-text-muted)";
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "10px 1fr", gap: "0 10px", alignItems: "start",
      padding: "7px 0", borderBottom: "1px solid var(--color-border-muted)",
    }}>
      <span style={{ fontSize: 9, color, fontWeight: 700, paddingTop: 3, fontFamily: "var(--font-mono)" }}>
        {(f.severity[0] ?? "?").toUpperCase()}
      </span>
      <div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--color-text-primary)" }}>
            {f.secret_type}
          </span>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{f.service}</span>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            {f.source}:{f.line}
          </span>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            {f.redacted_value}
          </span>
        </div>
        <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 2, lineHeight: 1.4 }}>
          {f.guidance}
        </div>
      </div>
    </div>
  );
}

function SecretScanSection({
  title, description, result, loading, onRun,
}: {
  title: string;
  description: string;
  result: CliJsonResponse<SecretScanData> | null;
  loading: boolean;
  onRun: () => void;
}) {
  const data = result?.data;
  const hasFindings = (data?.finding_count ?? 0) > 0;
  const shown = data?.findings.slice(0, 25) ?? [];
  const overflow = (data?.findings.length ?? 0) - shown.length;

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
        <div>
          <div className="eyebrow">{title}</div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>{description}</div>
        </div>
        <RunBtn loading={loading} hasResult={!!result} onRun={onRun} />
      </div>

      {result && !result.ok && (
        <div style={{ fontSize: 12, color: "var(--color-danger)" }}>{result.error ?? "Scan failed."}</div>
      )}

      {data && (
        <>
          <div style={{ display: "flex", gap: 16, fontSize: 11, color: "var(--color-text-muted)", marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 600, color: hasFindings ? "var(--color-danger)" : "var(--color-success)" }}>
              {data.finding_count} finding{data.finding_count !== 1 ? "s" : ""}
            </span>
            <span>{data.files_scanned} file{data.files_scanned !== 1 ? "s" : ""} scanned</span>
            {data.commits_scanned > 0 && <span>{data.commits_scanned} commits</span>}
            <span>{data.duration_ms}ms</span>
          </div>

          {hasFindings && Object.keys(data.severity_counts).length > 0 && (
            <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
              {Object.entries(data.severity_counts).map(([sev, count]) => (
                <span key={sev} style={{ fontSize: 11, color: SEVERITY_COLOR[sev] ?? "var(--color-text-muted)", fontWeight: 600 }}>
                  {count} {sev}
                </span>
              ))}
            </div>
          )}

          {!hasFindings && (
            <div style={{ fontSize: 12, color: "var(--color-success)", fontWeight: 500 }}>No secrets found.</div>
          )}

          {shown.map((f, i) => <SecretFindingRow key={i} f={f} />)}
          {overflow > 0 && (
            <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 8 }}>
              + {overflow} more finding{overflow !== 1 ? "s" : ""}
            </div>
          )}

          {data.errors.length > 0 && (
            <div style={{ marginTop: 10, fontSize: 11, color: "var(--color-warning)" }}>
              {data.errors.length} scan error{data.errors.length !== 1 ? "s" : ""}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function InjectionScanSection({
  result, loading, onRun,
}: {
  result: CliJsonResponse<InjectionScanData> | null;
  loading: boolean;
  onRun: () => void;
}) {
  const data = result?.data;
  const hasFindings = (data?.finding_count ?? 0) > 0;
  const shown = data?.findings.slice(0, 25) ?? [];
  const overflow = (data?.findings.length ?? 0) - shown.length;

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
        <div>
          <div className="eyebrow">Prompt Injection</div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>
            Scan files for embedded prompt injection patterns that could influence agent behavior.
          </div>
        </div>
        <RunBtn loading={loading} hasResult={!!result} onRun={onRun} />
      </div>

      {result && !result.ok && (
        <div style={{ fontSize: 12, color: "var(--color-danger)" }}>{result.error ?? "Scan failed."}</div>
      )}

      {data && (
        <>
          <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 10 }}>
            <span style={{ fontWeight: 600, color: hasFindings ? "var(--color-warning)" : "var(--color-success)" }}>
              {data.finding_count} pattern{data.finding_count !== 1 ? "s" : ""}
            </span>
            {" "}found in {data.target}
          </div>

          {!hasFindings && (
            <div style={{ fontSize: 12, color: "var(--color-success)", fontWeight: 500 }}>No injection patterns found.</div>
          )}

          {shown.map((f, i) => (
            <div key={i} style={{
              display: "grid", gridTemplateColumns: "10px 1fr", gap: "0 10px", alignItems: "start",
              padding: "7px 0", borderBottom: "1px solid var(--color-border-muted)",
            }}>
              <span style={{ fontSize: 9, color: SEVERITY_COLOR[f.severity] ?? "var(--color-text-muted)", fontWeight: 700, paddingTop: 3, fontFamily: "var(--font-mono)" }}>
                {(f.severity[0] ?? "?").toUpperCase()}
              </span>
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)" }}>{f.title}</span>
                  <span style={{ fontSize: 11, color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>{f.location}</span>
                  <span style={{ fontSize: 10, color: "var(--color-text-muted)" }}>{f.confidence} confidence</span>
                </div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 2, lineHeight: 1.4 }}>
                  {f.why_it_matters}
                </div>
              </div>
            </div>
          ))}
          {overflow > 0 && (
            <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 8 }}>
              + {overflow} more pattern{overflow !== 1 ? "s" : ""}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function ScanView() {
  const [dirResult,       setDirResult]       = useState<CliJsonResponse<SecretScanData> | null>(null);
  const [dirLoading,      setDirLoading]      = useState(false);
  const [stagedResult,    setStagedResult]    = useState<CliJsonResponse<SecretScanData> | null>(null);
  const [stagedLoading,   setStagedLoading]   = useState(false);
  const [historyResult,   setHistoryResult]   = useState<CliJsonResponse<SecretScanData> | null>(null);
  const [historyLoading,  setHistoryLoading]  = useState(false);
  const [injectionResult, setInjectionResult] = useState<CliJsonResponse<InjectionScanData> | null>(null);
  const [injectionLoading,setInjectionLoading]= useState(false);

  async function runScanDir() {
    setDirLoading(true);
    try {
      const r = await invoke<CliJsonResponse<SecretScanData>>("run_scan_dir", { path: null });
      setDirResult(r);
    } catch (e) {
      setDirResult({ ok: false, exit_code: -1, data: null as unknown as SecretScanData, error: String(e), stderr_summary: null });
    } finally {
      setDirLoading(false);
    }
  }

  async function runScanStaged() {
    setStagedLoading(true);
    try {
      const r = await invoke<CliJsonResponse<SecretScanData>>("run_scan_staged", { repo: null });
      setStagedResult(r);
    } catch (e) {
      setStagedResult({ ok: false, exit_code: -1, data: null as unknown as SecretScanData, error: String(e), stderr_summary: null });
    } finally {
      setStagedLoading(false);
    }
  }

  async function runScanHistory() {
    setHistoryLoading(true);
    try {
      const r = await invoke<CliJsonResponse<SecretScanData>>("run_scan_history", { repo: null, maxCommits: null });
      setHistoryResult(r);
    } catch (e) {
      setHistoryResult({ ok: false, exit_code: -1, data: null as unknown as SecretScanData, error: String(e), stderr_summary: null });
    } finally {
      setHistoryLoading(false);
    }
  }

  async function runScanInjection() {
    setInjectionLoading(true);
    try {
      const r = await invoke<CliJsonResponse<InjectionScanData>>("run_scan_injection", { path: null });
      setInjectionResult(r);
    } catch (e) {
      setInjectionResult({ ok: false, exit_code: -1, data: null as unknown as InjectionScanData, error: String(e), stderr_summary: null });
    } finally {
      setInjectionLoading(false);
    }
  }

  return (
    <div>
      <SecretScanSection
        title="Directory"
        description="Scan the current directory for secrets, credentials, and private keys."
        result={dirResult}
        loading={dirLoading}
        onRun={runScanDir}
      />
      <div style={{ marginTop: 20 }}>
        <SecretScanSection
          title="Staged Files"
          description="Scan git staged files before committing — pre-commit secret detection."
          result={stagedResult}
          loading={stagedLoading}
          onRun={runScanStaged}
        />
      </div>
      <div style={{ marginTop: 20 }}>
        <SecretScanSection
          title="Git History"
          description="Scan the last 200 commits for secrets that may have been committed and removed."
          result={historyResult}
          loading={historyLoading}
          onRun={runScanHistory}
        />
      </div>
      <div style={{ marginTop: 20 }}>
        <InjectionScanSection
          result={injectionResult}
          loading={injectionLoading}
          onRun={runScanInjection}
        />
      </div>
    </div>
  );
}
