import { CliJsonResponse, LockdownStatusData, WatchStatusData } from "../types";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 0", borderBottom: "1px solid var(--color-border-muted)" }}>
      <span style={{ width: 130, flex: "none", fontSize: 12.5, color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: 12.5, color: "var(--color-text-primary)", display: "flex", alignItems: "center", gap: 6 }}>{children}</span>
    </div>
  );
}

function Dot({ color }: { color: string }) {
  return <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, flex: "none", display: "inline-block" }} />;
}

interface LiveStatusCardProps {
  lockdownStatus: CliJsonResponse<LockdownStatusData> | null;
  watchStatus: CliJsonResponse<WatchStatusData> | null;
  loading: boolean;
  onRefresh: () => void;
}

export function LiveStatusCard({ lockdownStatus, watchStatus, loading, onRefresh }: LiveStatusCardProps) {
  const lockdown = lockdownStatus?.data;
  const watch = watchStatus?.data;

  return (
    <div style={{
      background: "var(--color-panel)", border: "1px solid var(--color-border-muted)",
      borderRadius: 12, overflow: "hidden",
    }}>
      <div style={{
        padding: "12px 18px", borderBottom: "1px solid var(--color-border-muted)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--color-text-primary)" }}>Live Status</div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="t focusable"
          style={{
            padding: "4px 12px", fontSize: 11.5, fontWeight: 600,
            background: "var(--color-elevated)", border: "1px solid var(--color-border-muted)",
            borderRadius: 6, color: "var(--color-text-muted)", cursor: "pointer",
            opacity: loading ? 0.5 : 1,
          }}
        >
          {loading ? "…" : "Refresh"}
        </button>
      </div>

      <div style={{ padding: "0 18px" }}>
        <Row label="Lockdown">
          {lockdown == null ? (
            <span style={{ color: "var(--color-text-muted)" }}>—</span>
          ) : lockdown.active ? (
            <>
              <Dot color="var(--color-danger)" />
              <span style={{ color: "var(--color-danger)", fontWeight: 700 }}>ACTIVE</span>
              {lockdown.reason && (
                <span style={{ color: "var(--color-text-muted)", fontSize: 11.5 }}>— {lockdown.reason}</span>
              )}
            </>
          ) : (
            <>
              <Dot color="var(--color-success)" />
              <span style={{ color: "var(--color-success)" }}>Inactive</span>
            </>
          )}
        </Row>

        <Row label="Watch daemon">
          {watch == null ? (
            <span style={{ color: "var(--color-text-muted)" }}>—</span>
          ) : watch.running ? (
            <>
              <Dot color="var(--color-success)" />
              <span style={{ color: "var(--color-success)" }}>Running</span>
              {watch.pid != null && (
                <span className="mono" style={{ color: "var(--color-text-muted)", fontSize: 11 }}>PID {watch.pid}</span>
              )}
            </>
          ) : watch.stale ? (
            <>
              <Dot color="var(--color-warning)" />
              <span style={{ color: "var(--color-warning)" }}>Stale PID file</span>
              {watch.pid != null && (
                <span className="mono" style={{ color: "var(--color-text-muted)", fontSize: 11 }}>PID {watch.pid}</span>
              )}
            </>
          ) : (
            <>
              <Dot color="var(--color-text-muted)" />
              <span style={{ color: "var(--color-text-muted)" }}>Not running</span>
            </>
          )}
        </Row>
      </div>
    </div>
  );
}
