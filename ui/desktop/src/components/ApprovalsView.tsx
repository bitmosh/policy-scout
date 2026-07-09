// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, ApprovalListData, ApprovalActionData, ApprovalItem } from "../types";
import { Motif } from "./BrandMark";

function isExpired(item: ApprovalItem): boolean {
  if (!item.expires_at) return false;
  return new Date(item.expires_at).getTime() < Date.now();
}

function fmtRelative(iso?: string | null): string {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function fmtExpiry(iso?: string | null): string {
  if (!iso) return "—";
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  if (diff < 0) return "expired";
  if (diff < 3600) return `${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr`;
  return `${Math.floor(diff / 86400)}d`;
}

function RiskDot({ score }: { score: number }) {
  const color = score >= 8 ? "var(--color-danger)"
    : score >= 6 ? "var(--color-warning)"
    : score >= 4 ? "var(--color-review)"
    : "var(--color-success)";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontVariantNumeric: "tabular-nums", fontSize: 12.5, fontWeight: 700, color,
    }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, flex: "none" }} />
      {score}/10
    </span>
  );
}

interface CommandGroup {
  command: string;
  items: ApprovalItem[];
  representative: ApprovalItem;
}

function groupByCommand(items: ApprovalItem[]): CommandGroup[] {
  const map = new Map<string, ApprovalItem[]>();
  for (const item of items) {
    const existing = map.get(item.command) ?? [];
    existing.push(item);
    map.set(item.command, existing);
  }
  return Array.from(map.entries()).flatMap(([command, group]) => {
    const sorted = group.slice().sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    if (!sorted[0]) return [];
    return [{ command, items: group, representative: sorted[0] }];
  });
}

function ApprovalGroupRow({ group, anyActionLoading, onApprove, onDeny }: {
  group: CommandGroup;
  anyActionLoading: boolean;
  onApprove: (ids: string[]) => void;
  onDeny: (ids: string[]) => void;
}) {
  const rep = group.representative;
  const count = group.items.length;
  const ids = group.items.map(i => i.approval_id);
  const expiries = group.items.map(i => i.expires_at).filter((x): x is string => !!x).sort();
  const newestExpiry = expiries.length ? expiries[expiries.length - 1] : null;

  return (
    <div style={{
      background: "var(--color-panel)", border: "1px solid var(--color-border-muted)",
      borderRadius: 10, overflow: "hidden",
    }}>
      <div style={{
        padding: "12px 16px", borderBottom: "1px solid var(--color-border-muted)",
        display: "flex", alignItems: "center", gap: 12,
      }}>
        <code className="mono" style={{
          flex: 1, fontSize: 12.5, color: "var(--color-text-primary)", fontWeight: 600,
          background: "var(--color-elevated)", padding: "4px 8px", borderRadius: 5,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {rep.command}
        </code>
        {count > 1 && (
          <span style={{
            fontSize: 11, fontWeight: 700, padding: "2px 7px", borderRadius: 20,
            background: "var(--color-elevated)", color: "var(--color-text-muted)",
            border: "1px solid var(--color-border-muted)", whiteSpace: "nowrap",
          }}>
            ×{count}
          </span>
        )}
        <RiskDot score={rep.risk_score} />
      </div>

      {rep.reasons.length > 0 && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--color-border-muted)" }}>
          <ul style={{ margin: 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 3 }}>
            {rep.reasons.map((r, i) => (
              <li key={i} style={{ fontSize: 12.5, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 16 }}>
        <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
          First requested {fmtRelative(
            group.items.map(i => i.created_at).sort()[0]
          )} · Expires in {fmtExpiry(newestExpiry)}
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button
            onClick={() => onDeny(ids)}
            disabled={anyActionLoading}
            style={{
              padding: "5px 14px", fontSize: 12.5, fontWeight: 600,
              cursor: anyActionLoading ? "default" : "pointer",
              background: "transparent", border: "1px solid var(--color-border)",
              borderRadius: 6, color: "var(--color-text-secondary)",
              opacity: anyActionLoading ? 0.5 : 1,
            }}
          >
            {count > 1 ? `Deny all ${count}` : "Deny"}
          </button>
          <button
            onClick={() => onApprove(ids)}
            disabled={anyActionLoading}
            style={{
              padding: "5px 14px", fontSize: 12.5, fontWeight: 600,
              cursor: anyActionLoading ? "default" : "pointer",
              background: "var(--color-success)", border: "none",
              borderRadius: 6, color: "#fff",
              opacity: anyActionLoading ? 0.5 : 1,
            }}
          >
            {anyActionLoading ? "…" : count > 1 ? `Approve all ${count}` : "Approve"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface ApprovalsViewProps {
  approvalsList: CliJsonResponse<ApprovalListData> | null;
  loading: boolean;
  actionResults: Record<string, CliJsonResponse<ApprovalActionData>>;
  actionLoading: Record<string, boolean>;
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
  onRefresh: () => void;
}

export function ApprovalsView({
  approvalsList, loading, actionResults, actionLoading, onApprove, onDeny, onRefresh,
}: ApprovalsViewProps) {
  const all = approvalsList?.data?.approvals ?? [];
  const active = all.filter(a => a.status === "pending" && !isExpired(a));
  const expiredCount = all.filter(a => a.status === "pending" && isExpired(a)).length;
  const groups = groupByCommand(active);

  // A group has any action in flight if any of its ids is loading
  function groupLoading(group: CommandGroup): boolean {
    return group.items.some(i => !!actionLoading[i.approval_id]);
  }

  // Banner feedback: collect results for a group's ids
  function groupResults(group: CommandGroup) {
    return group.items.map(i => actionResults[i.approval_id]).filter(Boolean);
  }

  // Bulk approve/deny: fire sequentially for each id
  function handleApproveGroup(ids: string[]) {
    for (const id of ids) onApprove(id);
  }
  function handleDenyGroup(ids: string[]) {
    for (const id of ids) onDeny(id);
  }

  return (
    <div className="scrollv" style={{ position: "absolute", inset: 0, padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text-primary)", letterSpacing: "-0.01em" }}>
            Pending Approvals
          </div>
          <div style={{ fontSize: 12.5, color: "var(--color-text-muted)", marginTop: 3 }}>
            Commands waiting for human review before they can run
          </div>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="t focusable"
          style={{
            padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer",
            background: "var(--color-elevated)", border: "1px solid var(--color-border-muted)",
            borderRadius: 7, color: "var(--color-text-secondary)", opacity: loading ? 0.5 : 1,
          }}
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {/* per-group action feedback */}
      {groups.map(group => {
        const results = groupResults(group);
        const last = results.length ? results[results.length - 1] : null;
        if (!last) return null;
        return (
          <div key={group.command} style={{
            marginBottom: 12, padding: "8px 14px", borderRadius: 8, fontSize: 12.5,
            background: last.ok
              ? "color-mix(in srgb, var(--color-success) 10%, var(--color-panel))"
              : "color-mix(in srgb, var(--color-danger) 10%, var(--color-panel))",
            border: `1px solid color-mix(in srgb, ${last.ok ? "var(--color-success)" : "var(--color-danger)"} 28%, transparent)`,
            color: last.ok ? "var(--color-success)" : "var(--color-danger)",
          }}>
            {last.ok
              ? `${last.data?.status === "approved_once" ? "Approved" : "Denied"}: ${group.command}`
              : `Failed: ${last.error ?? "Unknown error"}`}
          </div>
        );
      })}

      {loading && (
        <div style={{ padding: "60px 0", textAlign: "center", color: "var(--color-text-muted)", fontSize: 13 }}>
          Loading…
        </div>
      )}

      {!loading && groups.length === 0 && (
        <div style={{ padding: "60px 0", textAlign: "center" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}><Motif size={48} op={0.32} /></div>
          <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>No pending approvals</div>
          <div style={{ fontSize: 12.5, color: "var(--color-text-muted)", marginTop: 6 }}>
            Approvals appear here when a command returns REQUIRE_APPROVAL.
          </div>
        </div>
      )}

      {!loading && groups.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {groups.map(group => (
            <ApprovalGroupRow
              key={group.command}
              group={group}
              anyActionLoading={groupLoading(group)}
              onApprove={handleApproveGroup}
              onDeny={handleDenyGroup}
            />
          ))}
        </div>
      )}

      {!loading && expiredCount > 0 && (
        <div style={{
          marginTop: 20, fontSize: 11.5, color: "var(--color-text-muted)",
          textAlign: "center", padding: "8px 0",
        }}>
          {expiredCount} expired {expiredCount === 1 ? "entry" : "entries"} hidden
        </div>
      )}
    </div>
  );
}
