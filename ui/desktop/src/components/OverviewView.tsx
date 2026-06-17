import type { CliJsonResponse, DoctorStatusData, DataStatusData, AuditStatsData, AuditEventListData, SweepData } from "../types";
import { Chip } from "./Chip";
import { Motif } from "./BrandMark";
import { IcoChev } from "./Icons";

// ─── helpers ────────────────────────────────────────────────────

function fmtRelative(iso?: string | null): string {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function fmtBytes(b?: number): string {
  if (!b) return "—";
  return b > 1_000_000 ? `${(b / 1_000_000).toFixed(1)} MB` : `${(b / 1024).toFixed(0)} KB`;
}

export interface ReviewRowData {
  tone: string;
  kind: string;
  title: string;
  evidence: string;
  time: string;
  dim?: boolean;
}

export function deriveReviewRows(events?: AuditEventListData["events"]): ReviewRowData[] {
  if (!events) return [];
  return events
    .filter(e => {
      if (e.event_type !== "DecisionIssued") return false;
      const s = e.summary ?? "";
      return s.includes("DENY") || s.includes("SANDBOX_FIRST") || s.includes("REQUIRE_APPROVAL") || s.includes("COULD_NOT_VERIFY");
    })
    .slice(0, 8)
    .map(e => {
      const s = e.summary ?? "";
      let tone = "var(--color-info)";
      let kind = "DecisionIssued";
      let dim = false;
      if (s.includes("DENY_AND_ALERT")) { tone = "var(--color-danger)"; kind = "DENY_AND_ALERT"; }
      else if (s.includes("DENY")) { tone = "var(--color-danger)"; kind = "DENY"; }
      else if (s.includes("SANDBOX_FIRST")) { tone = "var(--color-warning)"; kind = "SANDBOX_FIRST"; }
      else if (s.includes("REQUIRE_APPROVAL")) { tone = "var(--color-review)"; kind = "REQUIRE_APPROVAL"; }
      else if (s.includes("COULD_NOT_VERIFY")) { tone = "var(--color-review)"; kind = "COULD_NOT_VERIFY"; dim = true; }
      const title = s.replace(/^Decision \S+ issued for:\s*/, "").trim() || s;
      return { tone, kind, title, evidence: title, time: fmtRelative(e.timestamp), dim };
    });
}

const EVENT_TONE: Record<string, string> = {
  DecisionIssued: "var(--color-info)",
  SweepCompleted: "var(--color-success)",
  ScoutReportGenerated: "var(--color-audit)",
  SandboxResultWritten: "var(--color-warning)",
  ApprovalRequested: "var(--color-review)",
  CommandExecutionBlocked: "var(--color-danger)",
};

// ─── sub-components ──────────────────────────────────────────────

function StackedBar({ total, allow, approval, sandbox, deny }: {
  total: number; allow: number; approval: number; sandbox: number; deny: number;
}) {
  if (!total) return <div style={{ height: 5, borderRadius: 3, background: "var(--color-elevated)" }} />;
  const seg = (n: number, c: string) => (
    <div style={{ width: `${(n / total * 100).toFixed(1)}%`, background: c, minWidth: n > 0 ? 2 : 0 }} />
  );
  return (
    <div style={{ display: "flex", height: 5, borderRadius: 3, overflow: "hidden", background: "var(--color-elevated)", gap: 1 }}>
      {seg(allow, "var(--color-success)")}
      {seg(approval, "var(--color-review)")}
      {seg(sandbox, "var(--color-warning)")}
      {seg(deny, "var(--color-danger)")}
    </div>
  );
}

const cardBody: React.CSSProperties = {
  padding: "14px 16px", display: "flex", flexDirection: "column",
  justifyContent: "space-between", gap: 8, minHeight: 104,
};

function PostureStrip({ sweeping, lastSweep, onSweep, onGoToSweeps, auditStats, doctorStatus, dataStatus, findingsCount }: {
  sweeping: boolean;
  lastSweep: string;
  onSweep: () => void;
  onGoToSweeps: () => void;
  auditStats?: CliJsonResponse<AuditStatsData> | null;
  doctorStatus?: CliJsonResponse<DoctorStatusData> | null;
  dataStatus?: CliJsonResponse<DataStatusData> | null;
  findingsCount?: number;
}) {
  const byType = auditStats?.data?.by_type ?? {};
  const total = (byType["DecisionIssued"] as number | undefined) ?? 0;
  const deny = (byType["CommandExecutionBlocked"] as number | undefined) ?? 0;
  const sandbox = ((byType["SandboxInstallCompleted"] as number | undefined) ?? 0) + ((byType["SandboxInstallStarted"] as number | undefined) ?? 0);
  const approval = (byType["ApprovalRequested"] as number | undefined) ?? 0;
  const allow = Math.max(0, total - deny - sandbox - approval);

  const checks = doctorStatus?.data?.checks ?? {};
  const healthy = Object.keys(checks).length > 0 && Object.values(checks).every(c => c.status === "ok");
  const dbSize = fmtBytes(dataStatus?.data?.audit_db_size_bytes);
  const cliMsg = checks["policy_scout_version"]?.message ?? "";
  const cliVer = cliMsg.replace("policy-scout ", "v") || "CLI";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
      <div className="card" style={cardBody}>
        <div className="eyebrow">Last 24h decisions</div>
        <div className="tnum" style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1, color: "var(--color-text-primary)" }}>
          {total || "—"}
        </div>
        <StackedBar total={total} allow={allow} approval={approval} sandbox={sandbox} deny={deny} />
        <div style={{ fontSize: 11.5, color: deny > 0 ? "var(--color-danger)" : "var(--color-text-muted)" }}>
          {deny > 0 ? `${deny} denied` : "No denials"}
        </div>
      </div>

      <div className="card" style={cardBody}>
        <div className="eyebrow">Open findings</div>
        <div className="tnum" style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1, color: "var(--color-text-primary)" }}>
          {findingsCount != null ? findingsCount : "—"}
        </div>
        <div style={{ height: 5 }} />
        <div style={{ fontSize: 11.5, color: "var(--color-text-muted)" }}>from latest sweep</div>
      </div>

      <div className="card" style={cardBody}>
        <div className="eyebrow">System</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="pulse" style={{ background: healthy ? "var(--color-success)" : "var(--color-warning)" }} />
          <span style={{ fontSize: 16, fontWeight: 600, color: healthy ? "var(--color-success)" : "var(--color-warning)" }}>
            {healthy ? "Healthy" : "Check system"}
          </span>
        </div>
        <div style={{ height: 5 }} />
        <div className="mono" style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
          {cliVer} · Audit DB {dbSize}
        </div>
      </div>

      <div className="card" style={cardBody}>
        <div className="eyebrow">Last sweep</div>
        {sweeping ? (
          <>
            <div style={{ position: "relative", height: 4, borderRadius: 3, background: "var(--color-elevated)", overflow: "hidden", marginTop: 4 }}>
              <div className="scanbar" />
            </div>
            <div style={{ height: 2 }} />
            <div className="mono" style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Scanning environment…</div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 22, fontWeight: 600, color: "var(--color-text-primary)" }}>{lastSweep}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span className="link focusable" tabIndex={0} role="button" onClick={onSweep}
                onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSweep(); } }}>
                Run quick sweep →
              </span>
              <span className="link focusable" tabIndex={0} role="button"
                style={{ color: "var(--color-text-muted)", fontSize: 11 }}
                onClick={onGoToSweeps}
                onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onGoToSweeps(); } }}>
                Go to Sweeps ›
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function SecHead({ title, count }: { title: string; count?: number }) {
  return (
    <div className="sec-head">
      <span style={{ fontSize: 15, fontWeight: 600, color: "var(--color-text-primary)" }}>{title}</span>
      {count != null && <span className="mono tnum" style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{count}</span>}
    </div>
  );
}

function ReviewRow({ row }: { row: ReviewRowData }) {
  return (
    <div className="review-row t">
      <div style={{ width: 3, background: row.tone, flex: "none" }} />
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 14, padding: "11px 14px", minWidth: 0 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
            <Chip tone={row.tone} dim={row.dim}>{row.kind}</Chip>
            <span className="ell" style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)" }}>{row.title}</span>
          </div>
          <div className="mono ell" style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 5 }}>{row.evidence}</div>
        </div>
        <span className="mono" style={{ fontSize: 11, color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>{row.time}</span>
        <span className="chev"><IcoChev /></span>
      </div>
    </div>
  );
}

function NeedsReviewSkeleton() {
  const headW = [50, 58, 44];
  const subW = [40, 32, 48];
  return (
    <section>
      <SecHead title="Needs review" />
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }} aria-busy="true" aria-live="polite">
        {[0, 1, 2].map(i => (
          <div key={i} style={{ display: "flex", background: "var(--color-panel)", border: "1px solid var(--color-border-muted)", borderRadius: 8, overflow: "hidden" }}>
            <div style={{ width: 3, background: "var(--color-elevated)", flex: "none" }} />
            <div style={{ flex: 1, padding: "12px 14px", display: "flex", alignItems: "center", gap: 14, minWidth: 0 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                  <span className="ps-shim" style={{ width: 96, height: 16 }} />
                  <span className="ps-shim" style={{ width: `${headW[i % 3]}%`, maxWidth: 320, height: 11 }} />
                </div>
                <span className="ps-shim" style={{ width: `${subW[i % 3]}%`, maxWidth: 260, height: 9, marginTop: 8 }} />
              </div>
              <span className="ps-shim" style={{ width: 52, height: 9, flex: "none" }} />
              <span className="ps-shim" style={{ width: 14, height: 14, flex: "none" }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function NeedsReview({ rows }: { rows: ReviewRowData[] }) {
  return (
    <section>
      <SecHead title="Needs review" count={rows.length} />
      {rows.length === 0 ? (
        <div style={{ padding: "52px 0", textAlign: "center" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}><Motif size={52} op={0.6} /></div>
          <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>Nothing needs review right now</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {rows.map((r, i) => <ReviewRow key={i} row={r} />)}
        </div>
      )}
    </section>
  );
}

function RecentActivity({ auditEventsList }: { auditEventsList?: CliJsonResponse<AuditEventListData> | null }) {
  const events = auditEventsList?.data?.events?.slice(0, 8) ?? [];
  return (
    <section>
      <SecHead title="Recent activity" />
      {events.length === 0 ? (
        <div style={{ padding: "28px 0", textAlign: "center" }}>
          <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>No recent activity</div>
        </div>
      ) : (
        <div className="act-list">
          {events.map((e, i) => {
            const tone = EVENT_TONE[e.event_type ?? ""] ?? "var(--color-text-muted)";
            return (
              <div className="act-row t" key={e.event_id ?? i}>
                <Chip tone={tone} size={9}>{e.event_type}</Chip>
                <span className="ell" style={{ flex: 1, fontSize: 12.5, color: "var(--color-text-secondary)" }}>
                  {e.summary ?? e.event_type}
                </span>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                  {fmtRelative(e.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ─── attention banner ─────────────────────────────────────────────

interface AttentionSpec {
  color: string;
  message: string;
  action?: { label: string; onClick: () => void };
}

function pickAttention(
  doctorStatus: CliJsonResponse<DoctorStatusData> | null | undefined,
  reviewRows: ReviewRowData[],
  policyIssueCount: number,
  findingsCount: number | undefined,
  onGoToAudit?: () => void,
  onGoToPolicy?: () => void,
  onGoToSystem?: () => void,
): AttentionSpec | null {
  const checks = doctorStatus?.data?.checks ?? {};
  const healthy = Object.keys(checks).length > 0
    && Object.values(checks).every(c => c.status === "ok");
  if (!healthy && Object.keys(checks).length > 0) {
    return { color: "var(--color-warning)", message: "System check found issues.", action: onGoToSystem ? { label: "Go to System →", onClick: onGoToSystem } : undefined };
  }
  const blocked = reviewRows.filter(r => r.kind === "DENY" || r.kind === "DENY_AND_ALERT").length;
  if (blocked > 0) {
    return { color: "var(--color-danger)", message: `${blocked} blocked command${blocked > 1 ? "s" : ""} need review.`, action: onGoToAudit ? { label: "Go to Audit →", onClick: onGoToAudit } : undefined };
  }
  if (reviewRows.length > 0) {
    return { color: "var(--color-review)", message: `${reviewRows.length} item${reviewRows.length > 1 ? "s" : ""} need review.`, action: onGoToAudit ? { label: "Go to Audit →", onClick: onGoToAudit } : undefined };
  }
  if (policyIssueCount > 0) {
    return { color: "var(--color-warning)", message: `Policy has ${policyIssueCount} issue${policyIssueCount > 1 ? "s" : ""}.`, action: onGoToPolicy ? { label: "Go to Policy →", onClick: onGoToPolicy } : undefined };
  }
  if (findingsCount != null && findingsCount > 0) {
    return { color: "var(--color-warning)", message: `${findingsCount} open finding${findingsCount > 1 ? "s" : ""} from last sweep.` };
  }
  return null;
}

function AttentionBanner({ spec }: { spec: AttentionSpec }) {
  return (
    <div style={{
      marginBottom: 16,
      display: "flex", alignItems: "center", gap: 10,
      padding: "9px 14px",
      background: `color-mix(in srgb, ${spec.color} 9%, var(--color-panel))`,
      border: `1px solid color-mix(in srgb, ${spec.color} 28%, transparent)`,
      borderRadius: 8,
    }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: spec.color, flex: "none" }} />
      <span style={{ flex: 1, fontSize: 12.5, color: "var(--color-text-secondary)" }}>{spec.message}</span>
      {spec.action && (
        <button onClick={spec.action.onClick} style={{
          background: "transparent", border: "none", padding: 0,
          fontSize: 12, fontWeight: 600, color: spec.color, cursor: "pointer",
        }}>
          {spec.action.label}
        </button>
      )}
    </div>
  );
}

// ─── public view component ────────────────────────────────────────

export interface OverviewViewProps {
  doctorStatus?: CliJsonResponse<DoctorStatusData> | null;
  dataStatus?: CliJsonResponse<DataStatusData> | null;
  auditStats?: CliJsonResponse<AuditStatsData> | null;
  auditEventsList?: CliJsonResponse<AuditEventListData> | null;
  quickSweep?: CliJsonResponse<SweepData> | null;
  sweeping: boolean;
  lastSweepLabel: string;
  reviewLoading: boolean;
  reviewRows: ReviewRowData[];
  policyIssueCount?: number;
  onSweep: () => void;
  onGoToSweeps: () => void;
  onGoToAudit?: () => void;
  onGoToPolicy?: () => void;
  onGoToSystem?: () => void;
}

export function OverviewView({
  doctorStatus, dataStatus, auditStats, auditEventsList, quickSweep,
  sweeping, lastSweepLabel, reviewLoading, reviewRows,
  policyIssueCount = 0, onSweep, onGoToSweeps, onGoToAudit, onGoToPolicy, onGoToSystem,
}: OverviewViewProps) {
  const findingsCount = quickSweep?.data?.findings?.length;
  const attention = pickAttention(doctorStatus, reviewRows, policyIssueCount, findingsCount, onGoToAudit, onGoToPolicy, onGoToSystem);

  return (
    <div className="scrollv" style={{ position: "absolute", inset: 0, padding: 24 }}>
      {attention && <AttentionBanner spec={attention} />}
      <PostureStrip
        sweeping={sweeping}
        lastSweep={lastSweepLabel}
        onSweep={onSweep}
        onGoToSweeps={onGoToSweeps}
        auditStats={auditStats}
        doctorStatus={doctorStatus}
        dataStatus={dataStatus}
        findingsCount={findingsCount}
      />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.6fr) minmax(0, 1fr)", gap: 24, marginTop: 24, alignItems: "start" }}>
        {reviewLoading ? <NeedsReviewSkeleton /> : <NeedsReview rows={reviewRows} />}
        <RecentActivity auditEventsList={auditEventsList} />
      </div>

      <div style={{ marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--color-border-muted)", fontSize: 11.5, color: "var(--color-text-muted)", textAlign: "center", letterSpacing: "0.01em" }}>
        Local-first · No remote upload · Commands never executed from this UI.
      </div>
    </div>
  );
}

export function Placeholder({ label }: { label: string }) {
  return (
    <div style={{ height: "100%", display: "grid", placeItems: "center", padding: 24 }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}><Motif size={50} op={0.32} /></div>
        <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>{label}</div>
        <div style={{ fontSize: 12.5, color: "var(--color-text-muted)", marginTop: 6 }}>Coming in the next pass.</div>
      </div>
    </div>
  );
}
