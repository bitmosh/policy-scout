# UI ↔ Backend Coverage Audit

**Date:** 2026-06-12  
**Scope:** Tauri invoke handlers (`ui/desktop/src-tauri/src/lib.rs`) vs. CLI commands (`policy_scout/cli/main.py`) vs. what the React UI (`ui/desktop/src/App.tsx`) actually calls.

---

## 1. Tauri Invoke Handler Coverage

16 Tauri handlers are registered. 14 are called from the UI. 2 are partial or missing.

| Handler | CLI command it calls | UI wired? | Where |
|---|---|---|---|
| `get_doctor_status` | `doctor --json` | ✓ | System view, Overview mount |
| `get_data_status` | `data status --json` | ✓ | System view, Overview mount |
| `get_audit_stats` | `audit stats --json` | ✓ | Overview mount |
| `get_cleanup_dry_run(target)` | `data cleanup --target <t> --dry-run --json` | ✓ (dry-run only) | System view |
| `run_eval` | `eval run --json` | ✓ | System view |
| `run_sweep_quick` | `sweep quick --json` | ✓ | Sweeps view, Overview |
| `run_sweep_project` | `sweep project --json` | ✓ | Sweeps view |
| `check_command(command_text)` | `check --json <cmd>` | ✓ | Check view (DecisionCheckCard) |
| `list_sandbox_results(limit, offset)` | `report list --type sandbox_result` | ✓ | Sandbox view |
| `list_reports_filtered(limit, type, offset)` | `report list --json` | ✓ | Reports view |
| `show_report(report_id)` | `report show <id> --json` | ✓ | Reports detail |
| `show_sandbox_result(report_id)` | `report show <id> --json` | ✓ | Sandbox detail |
| `list_audit_events_filtered(event_type, limit, offset)` | `audit list / audit type --json` | ✓ | Audit view |
| `show_audit_event(event_id)` | `audit show <id> --json` | ✓ | Audit detail |
| `get_policy_overview` | `policy show --json` | ⚠️ partial | Fetched on mount, state exists, **no view renders it** |
| `run_policy_validate` | `policy validate --json` | ✗ | Handler registered, `PolicyValidateCard.tsx` exists, but state was removed from App.tsx and no view mounts the card |

### Handler-level gaps

- **`get_policy_overview` state is orphaned.** App.tsx fetches it on mount and stores it in `policyOverview`, but no view renders `PolicyOverviewCard`. The card component and types exist — it just needs a view.
- **`run_policy_validate` is fully disconnected.** The Rust handler is registered, `PolicyValidateCard.tsx` exists, but `policyValidate` state was removed from App.tsx during the shell pass. No view mounts the card.
- **No cleanup execute handler.** `get_cleanup_dry_run` shows the plan. There is no `run_cleanup_apply` handler, so the actual deletion (`data cleanup --apply`) is unreachable from the UI. `CleanupDryRunCard` is read-only.

---

## 2. CLI Commands with No Tauri Handler

The following CLI subcommands exist and work from the terminal, but have zero Tauri handler coverage and are completely inaccessible from the desktop UI.

### High priority — core workflow features

| CLI command | What it does | Gap impact |
|---|---|---|
| `approvals list / show / approve / deny` | Review and resolve pending `REQUIRE_APPROVAL` decisions. Approvals are created when the check returns `REQUIRE_APPROVAL`, but the user has no way to view or action them in the UI. | High — the whole approval queue is invisible |
| `sandbox -- npm install <pkg>` | Run a package install in an isolated temp workspace, capture lifecycle scripts, supply chain findings, and transitive dep analysis. Core security workflow. | High — sandbox install is only CLI-accessible |
| `sandbox <sbx_id>` (migrate mode) | After reviewing a sandbox result, apply the approved package files to the host. | High — without migrate, sandbox results are read-only dead ends |
| `run <command>` | Execute a command through the full policy gate (ALLOW path executes it, REQUIRE_APPROVAL path creates an approval). | High — the UI can *check* commands but not *run* them |
| `data cleanup --apply` | Execute the deletion plan shown by the dry-run. | Medium — dry-run plan is shown, but users can't apply it |

### Medium priority — operational visibility

| CLI command | What it does | Gap impact |
|---|---|---|
| `lockdown on / off / status` | Emergency lockdown mode that denies all non-read ops. Status is not surfaced anywhere in the UI. | High for incident response — lockdown indicator in TopBar is visual only, not data-backed |
| `scan dir / file / staged / history` | Secrets scanning across files and git history. Entirely separate scan surface. | Medium |
| `scan injection` | Prompt injection pattern detection across files. | Medium |
| `audit verify-chain` | Verify HMAC chain integrity of the JSONL audit log — confirms the audit trail hasn't been tampered. | Medium |
| `audit request <request_id>` | Show all events for a single request_id. Useful for tracing a command end-to-end. | Low — workaround is audit type filter |
| `canary install / check / remove` | Place and verify prompt-injection canary files in a project. | Medium |
| `policy simulate <command>` | Show the full rule trace for a command (which rules fired, in what order, why). Richer than `check`. | Medium |
| `policy test --against-history` | Re-simulate historical decisions against the current policy — regression testing for rule changes. | Medium |
| `intel status / clear-cache / evict-expired` | Threat intel cache status and management. | Low |
| `watch start / stop / status / logs` | Continuous filesystem watch daemon. Status not surfaced in UI. | Medium |

### Lower priority — advanced / infrastructure

| CLI command | What it does |
|---|---|
| `integrity check` | Verify registry file checksums against manifest |
| `preserve` | Capture system-state evidence archive (incident response) |
| `clearance` | Post-incident clearance checks before deactivating lockdown |
| `git context / hooks / lockfile-check / staged-check` | Git integration management |
| `policy commit` | Snapshot policy registry state into git |
| `sandbox-run` | General-purpose namespace sandbox for arbitrary commands |
| `sandbox-check-prereqs` | Check sandbox prerequisites |
| `report export` | Export a Scout Report to markdown or JSON file |
| `serve mcp / install / status` | MCP server management |
| `demo` | Run the safe local demonstration |

---

## 3. View Coverage Summary

All 7 nav views are functional (no Placeholder fallback in production code):

| View | Status | Notes |
|---|---|---|
| Overview | ✓ full | posture strip, needs-review, recent activity |
| Check | ✓ full | DecisionCheckCard with `check_command` |
| Reports | ✓ full | list + paginate + detail |
| Audit | ✓ full | list + type filter + paginate + detail |
| Sweeps | ✓ full | quick sweep + project sweep |
| Sandbox | ✓ full | list + paginate + detail. **No launch UI** — results only |
| System | ✓ full | doctor, data status, eval, cleanup dry-run |

### Missing UI for existing handler coverage

- **No Policy view.** `get_policy_overview` and `run_policy_validate` are both Tauri-registered. `PolicyOverviewCard.tsx` and `PolicyValidateCard.tsx` both exist. A "Policy" nav item + view would wire them.
- **Sandbox view shows results only.** The Sandbox view reads past results. There's no input field to launch a new sandbox install (the `sandbox -- npm install <pkg>` workflow). This is the most common active use of the sandbox feature.
- **No Approvals panel.** The system generates pending approvals, but users can't see or action them. No Tauri handler + no view.
- **Lockdown indicator is decorative.** The padlock icon in TopBar is static. `lockdown status` has no Tauri handler — the real state is never fetched.

---

## 4. Recommended Next Steps (prioritized)

1. **Wire the orphaned policy cards.** Add a "Policy" view (or fold into System) that renders `PolicyOverviewCard` + `PolicyValidateCard`. Two handlers already registered, two cards already built. Lowest effort / highest payoff.

2. **Add cleanup execute.** Add a `run_cleanup_apply(target)` Rust handler that calls `data cleanup --target <t> --apply --yes --json`. Wire an "Apply" button in `CleanupDryRunCard`. Dry-run shows the plan; the button should execute it.

3. **Add Approvals view.** New Tauri handlers: `list_approvals`, `approve_request(approval_id)`, `deny_request(approval_id)`. New view: pending approvals list with approve/deny actions per row.

4. **Add Sandbox launch UI.** Add a command input in the Sandbox view (like `DecisionCheckCard`) that calls a new `run_sandbox_install(command)` handler → `sandbox -- <cmd> --json`. Results auto-refresh into the list.

5. **Add lockdown status fetch.** New handler `get_lockdown_status` → `lockdown status --json`. Feed it into System view and/or the TopBar padlock indicator.

6. **Wire policy simulate.** New handler `run_policy_simulate(command)` → `policy simulate <cmd> --json`. Could be a tab inside the Check view alongside the current decision output.

7. **Wire scan commands.** New handlers for `run_scan_dir(path)`, `run_scan_staged()`, `run_scan_history()`. New Scans view or fold into System.

---

## 5. Files Referenced

| File | Role |
|---|---|
| `ui/desktop/src-tauri/src/lib.rs` | Tauri invoke handler registry |
| `policy_scout/cli/main.py` | Full CLI command surface |
| `ui/desktop/src/App.tsx` | All invoke calls + view routing |
| `ui/desktop/src/components/PolicyOverviewCard.tsx` | Built, not mounted |
| `ui/desktop/src/components/PolicyValidateCard.tsx` | Built, not mounted |
| `ui/desktop/src/components/CleanupDryRunCard.tsx` | Read-only, no apply action |
| `ui/desktop/src/components/DecisionCheckCard.tsx` | Calls `check_command` directly |
