# Implementation Plan — Gap 11: Desktop UI Improvements

## Problem
The Tauri dashboard is read-only. It shows data but cannot act. The approval workflow requires switching to a terminal. There's no real-time feed of events as they happen. Sweep results are point-in-time with no comparison across runs.

## Goal
Four targeted additions: approval workflow from the UI, real-time audit event stream, risk trend chart, and sweep diff view. All maintain the CLI-as-authority principle — the UI calls the CLI, never bypasses it.

---

## Affected Files

```
ui/desktop/src-tauri/src/lib.rs              # new Tauri commands
ui/desktop/src/components/
├── ApprovalCard.tsx                          # MODIFY: add approve/deny actions
├── AuditEventStream.tsx                      # NEW: real-time event feed
├── RiskTrendChart.tsx                        # NEW: decisions over time
├── SweepDiffView.tsx                         # NEW: delta between sweeps
└── LiveBadge.tsx                             # NEW: "live" indicator for streaming
ui/desktop/src/hooks/
└── useAuditStream.ts                         # NEW: JSONL tail hook
ui/desktop/src/types/
└── stream.ts                                 # NEW: stream event types
```

---

## Implementation Approach

### Step 1 — Approval Workflow

**Rust side (`lib.rs`):** Add two new Tauri commands with the same strict validation as existing commands:

```rust
#[tauri::command]
fn approve_request(approval_id: String) -> Result<String, String> {
    // Validate: approval_id must match "^apr_[a-zA-Z0-9]{8,32}$"
    let re = Regex::new(r"^apr_[a-zA-Z0-9]{8,32}$").unwrap();
    if !re.is_match(&approval_id) {
        return Err("Invalid approval ID format".to_string());
    }
    run_cli_command(&["approvals", "approve", &approval_id, "--json"])
}

#[tauri::command]
fn deny_request(approval_id: String) -> Result<String, String> {
    let re = Regex::new(r"^apr_[a-zA-Z0-9]{8,32}$").unwrap();
    if !re.is_match(&approval_id) {
        return Err("Invalid approval ID format".to_string());
    }
    run_cli_command(&["approvals", "deny", &approval_id, "--json"])
}
```

**React side (`ApprovalCard.tsx`):** The existing card shows pending approvals. Add `Approve` and `Deny` buttons with a confirmation step before acting:

```tsx
const ApprovalCard: React.FC<{ approval: ApprovalRequest }> = ({ approval }) => {
  const [confirming, setConfirming] = useState<'approve' | 'deny' | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleAction = async (action: 'approve' | 'deny') => {
    if (confirming !== action) {
      setConfirming(action);  // first click: show confirmation
      return;
    }
    setLoading(true);
    try {
      const fn = action === 'approve' ? approveRequest : denyRequest;
      await fn(approval.approval_id);
      setResult(action === 'approve' ? 'Approved' : 'Denied');
    } catch (err) {
      setResult(`Error: ${err}`);
    } finally {
      setLoading(false);
      setConfirming(null);
    }
  };

  if (result) {
    return <div className="approval-result">{result}</div>;
  }

  return (
    <div className="approval-card">
      <ApprovalDetails approval={approval} />
      <div className="approval-actions">
        <button
          onClick={() => handleAction('deny')}
          className={confirming === 'deny' ? 'btn-confirm-deny' : 'btn-deny'}
          disabled={loading}
        >
          {confirming === 'deny' ? 'Confirm Deny' : 'Deny'}
        </button>
        <button
          onClick={() => handleAction('approve')}
          className={confirming === 'approve' ? 'btn-confirm-approve' : 'btn-approve'}
          disabled={loading}
        >
          {confirming === 'approve' ? 'Confirm Approve' : 'Approve'}
        </button>
      </div>
    </div>
  );
};
```

**Safety note:** The two-click confirmation pattern prevents accidental approvals. The first click shows "Confirm Approve" / "Confirm Deny"; only the second click executes. This matches best practice for irreversible UI actions.

### Step 2 — Real-Time Audit Event Stream

**Rust side:** Tauri's file system watching (`tauri-plugin-fs-watch`) can monitor the JSONL file. On each new line, emit a Tauri event to the frontend.

Add to `lib.rs`:

```rust
use tauri::Manager;
use std::io::{BufRead, Seek, SeekFrom};

#[tauri::command]
async fn start_audit_stream(app: tauri::AppHandle) -> Result<(), String> {
    let audit_path = get_audit_jsonl_path()?;
    
    tokio::spawn(async move {
        let mut file = std::fs::File::open(&audit_path)
            .map_err(|e| e.to_string())?;
        file.seek(SeekFrom::End(0)).ok();  // start from end
        
        let mut reader = std::io::BufReader::new(file);
        let mut line = String::new();
        
        loop {
            line.clear();
            match reader.read_line(&mut line) {
                Ok(0) => {
                    tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                }
                Ok(_) => {
                    let trimmed = line.trim().to_string();
                    if !trimmed.is_empty() {
                        app.emit("audit-event", trimmed).ok();
                    }
                }
                Err(_) => break,
            }
        }
        Ok::<(), String>(())
    });
    
    Ok(())
}
```

**React side (`useAuditStream.ts`):**

```typescript
import { useEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';

export interface AuditEventRaw {
  event_id: string;
  event_type: string;
  timestamp: string;
  summary: string;
  actor?: { type: string };
  chain_seq?: number;
}

export function useAuditStream(maxEvents = 100) {
  const [events, setEvents] = useState<AuditEventRaw[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    invoke('start_audit_stream').then(() => setConnected(true));

    const unlisten = listen<string>('audit-event', (event) => {
      try {
        const parsed: AuditEventRaw = JSON.parse(event.payload);
        setEvents(prev => [parsed, ...prev].slice(0, maxEvents));
      } catch {
        // ignore malformed lines
      }
    });

    return () => {
      unlisten.then(fn => fn());
      setConnected(false);
    };
  }, [maxEvents]);

  return { events, connected };
}
```

**React component (`AuditEventStream.tsx`):**

```tsx
export const AuditEventStream: React.FC = () => {
  const { events, connected } = useAuditStream(50);

  return (
    <div className="audit-stream">
      <div className="stream-header">
        <h3>Live Audit Stream</h3>
        <LiveBadge connected={connected} />
      </div>
      <div className="stream-events">
        {events.map(event => (
          <AuditEventRow key={event.event_id} event={event} />
        ))}
        {events.length === 0 && (
          <div className="stream-empty">Waiting for events…</div>
        )}
      </div>
    </div>
  );
};
```

### Step 3 — Risk Trend Chart

The existing `audit stats` command returns counts per decision type. Extend it to return a time-bucketed breakdown.

**New Rust command:**

```rust
#[tauri::command]
fn get_risk_trend(days: u32) -> Result<String, String> {
    if days == 0 || days > 90 {
        return Err("days must be between 1 and 90".to_string());
    }
    run_cli_command(&["audit", "stats", "--trend", "--days", &days.to_string(), "--json"])
}
```

**New CLI flag in `cli/audit.py`:**

```python
# policy-scout audit stats --trend --days 7 --json
# Returns: {"buckets": [{"date": "2026-06-04", "ALLOW": 45, "DENY": 3, "SANDBOX_FIRST": 12, ...}, ...]}
```

**React component (`RiskTrendChart.tsx`):**

Use the `recharts` library if already in `node_modules`, otherwise implement a simple SVG bar chart directly (no new dependency). The chart shows stacked bars per day, colored by decision type.

```tsx
// If recharts is available:
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const DECISION_COLORS = {
  ALLOW: '#22c55e',
  ALLOW_LOGGED: '#86efac',
  REQUIRE_APPROVAL: '#f59e0b',
  SANDBOX_FIRST: '#3b82f6',
  DENY: '#ef4444',
  DENY_AND_ALERT: '#7f1d1d',
};

export const RiskTrendChart: React.FC<{ days?: number }> = ({ days = 14 }) => {
  const [data, setData] = useState<TrendBucket[]>([]);
  
  useEffect(() => {
    invoke<string>('get_risk_trend', { days })
      .then(raw => setData(JSON.parse(raw).buckets));
  }, [days]);

  return (
    <div className="risk-trend">
      <h3>Decision Trend ({days} days)</h3>
      <BarChart width={600} height={200} data={data}>
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        {Object.entries(DECISION_COLORS).map(([decision, color]) => (
          <Bar key={decision} dataKey={decision} stackId="a" fill={color} />
        ))}
      </BarChart>
    </div>
  );
};
```

**If recharts is not available:** A pure-CSS/SVG bar chart using native browser APIs is ~100 lines and avoids a new dependency.

### Step 4 — Sweep Diff View

**How it works:** Each sweep is stored as a Scout Report. Compare the findings of the two most recent project sweeps (or two selected sweeps) to show what changed.

**New Rust command:**

```rust
#[tauri::command]
fn get_sweep_diff(report_id_a: String, report_id_b: String) -> Result<String, String> {
    validate_report_id(&report_id_a)?;
    validate_report_id(&report_id_b)?;
    run_cli_command(&["report", "diff", &report_id_a, &report_id_b, "--json"])
}
```

**New CLI subcommand `report diff`:**

```python
def diff_reports(report_id_a: str, report_id_b: str) -> SweepDiff:
    report_a = get_report(report_id_a)
    report_b = get_report(report_id_b)
    
    findings_a = {f.finding_id: f for f in report_a.findings}
    findings_b = {f.finding_id: f for f in report_b.findings}
    
    # Match findings by (category, location) since finding_id changes between runs
    def finding_key(f: Finding) -> tuple:
        return (f.category, f.location)
    
    keys_a = {finding_key(f) for f in report_a.findings}
    keys_b = {finding_key(f) for f in report_b.findings}
    
    return SweepDiff(
        new_findings=[f for f in report_b.findings if finding_key(f) not in keys_a],
        resolved_findings=[f for f in report_a.findings if finding_key(f) not in keys_b],
        persisting_findings=[f for f in report_b.findings if finding_key(f) in keys_a],
        report_a_timestamp=report_a.created_at,
        report_b_timestamp=report_b.created_at,
    )
```

**React component (`SweepDiffView.tsx`):**

```tsx
export const SweepDiffView: React.FC = () => {
  const [diff, setDiff] = useState<SweepDiff | null>(null);
  // Load the two most recent project sweep reports automatically

  return (
    <div className="sweep-diff">
      <h3>Sweep Changes</h3>
      {diff && (
        <>
          <DiffSection
            label="New findings"
            findings={diff.new_findings}
            variant="new"
          />
          <DiffSection
            label="Resolved"
            findings={diff.resolved_findings}
            variant="resolved"
          />
          <DiffSection
            label="Persisting"
            findings={diff.persisting_findings}
            variant="persisting"
          />
        </>
      )}
    </div>
  );
};
```

---

## Integration Points

- `ui/desktop/src-tauri/src/lib.rs` — new commands: `approve_request`, `deny_request`, `start_audit_stream`, `get_risk_trend`, `get_sweep_diff`
- `cli/audit.py` — add `--trend --days N` flag to `stats` subcommand
- `cli/report.py` — add `diff <id_a> <id_b>` subcommand
- `reports/scout_report.py` — `SweepDiff` data model

---

## Test Strategy

- Unit test Rust validation for `approve_request` and `deny_request` with invalid ID formats
- Unit test `report diff` logic with fixture reports (new, resolved, persisting findings)
- Unit test trend bucketing in `audit stats`
- Integration test: verify approval UI calls `approvals approve` CLI command with correct ID
- Manual verification required for: real-time stream (start a watch, trigger an event, verify it appears), chart rendering, diff view layout

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| Approval Rust commands | ~60 | Low |
| ApprovalCard approve/deny UI | ~100 | Low |
| Audit stream Rust command | ~80 | Medium |
| `useAuditStream` hook | ~60 | Low |
| `AuditEventStream` component | ~80 | Low |
| `LiveBadge` component | ~30 | Low |
| Risk trend CLI flag | ~60 | Low |
| `get_risk_trend` Rust command | ~40 | Low |
| `RiskTrendChart` component | ~100 | Low-Medium |
| Sweep diff CLI subcommand | ~120 | Medium |
| `get_sweep_diff` Rust command | ~60 | Low |
| `SweepDiffView` component | ~100 | Low |
| Tests | ~300 | Medium |
| **Total** | **~1190** | |

---

## Open Questions

1. Should the audit stream start automatically on app open, or require user activation? Recommendation: start automatically and show a `LiveBadge` indicator — the stream is lightweight (file tail, no network) and always useful.
2. Should the approval card require the user to read the full decision detail before enabling the confirm button? Recommendation: yes — show a short time delay (2s) before the confirm button becomes clickable. This is a minimal friction brake against hasty approvals.
3. Should chart data be re-fetched on a timer or only on user action? Recommendation: refetch every 30 seconds while the trend card is in view. Use React's `IntersectionObserver` to pause polling when the card is off-screen.
