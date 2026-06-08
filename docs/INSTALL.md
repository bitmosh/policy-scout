# Policy Scout Installation and Development Setup

## Purpose

This document provides a complete fresh-install and development setup guide for Policy Scout v0.1-alpha. It covers Python CLI setup, desktop UI development, data locations, verification commands, and safety boundaries.

**Supported local development target:** Linux (Ubuntu/Debian primary, other Linux distros may work with dependency adjustments).

## Shipping Model

**CLI-first, desktop dogfooded.**

- The CLI is the source of truth for policy decisions, audit, reports, sweeps, and JSON contracts.
- The Tauri desktop app is an optional read-only/check-only companion.
- The desktop app does not replace the CLI authority.
- The desktop app should be verified with the same green checkpoint commands plus native smoke before use.
- Decision Check remains check-only and calls `policy-scout check --json` through a bounded adapter.
- No command execution, approval resolution, sandbox migration, cleanup deletion, shell plugin, or arbitrary argv UI is shipped in v0.4.

---

## System Requirements

### Python CLI
- Python 3.12 or higher
- pip (comes with Python)
- Virtual environment (recommended): `python -m venv`

### Desktop UI (optional)
- Node.js 22 or higher
- npm or yarn
- Rust stable toolchain
- Linux system dependencies for Tauri:
  - `libwebkit2gtk-4.1-dev`
  - `libappindicator3-dev`
  - `librsvg2-dev`
  - `patchelf`

---

## Python Setup

### 1. Clone the repository

```bash
git clone https://github.com/bitmosh/policy-scout.git
cd policy-scout
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

Using a virtual environment avoids externally-managed Python issues on some systems.

### 3. Install Policy Scout in editable mode

```bash
pip install -e ".[dev]"
```

This installs:
- The `policy-scout` console script
- Runtime dependencies (pyyaml)
- Development dependencies (pytest)

### 4. Verify installation

```bash
policy-scout doctor
```

You should see health diagnostics output indicating successful installation.

---

## CLI Verification

Run these commands to verify the CLI is working correctly:

```bash
# Health diagnostics
policy-scout doctor --json

# Evaluation suite (44 test cases)
policy-scout eval run

# Check a safe command
policy-scout check -- ls

# Check a risky command
policy-scout check -- npm install lodash
```

---

## Desktop Setup (Optional)

The desktop UI is an experimental read-only dashboard. It is not required for CLI development.

### 1. Install Node dependencies

```bash
cd ui/desktop
npm install
```

### 2. Build the frontend

```bash
npm run build
```

This runs TypeScript compilation and Vite build.

### 3. Install system dependencies for Tauri (Linux)

```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
```

### 4. Verify Rust backend

```bash
cd src-tauri
cargo check
cargo test
```

### 5. Launch the native app

```bash
cd /path/to/policy-scout/ui/desktop
npm run tauri dev
```

This launches the native Tauri application window with live CLI data.

### Browser preview (static layout only)

```bash
npm run dev
```

Opens a browser at http://localhost:1420. This mode cannot load live CLI data (Tauri invoke APIs unavailable in browser context).

---

## Data Locations

Policy Scout stores all data locally under `~/.local/share/policy-scout/` by default.

### Default paths

- **Audit store (SQLite):** `~/.local/share/policy-scout/audit.db`
- **Audit stream (JSONL):** `~/.local/share/policy-scout/audit.jsonl`
- **Approvals:** `~/.local/share/policy-scout/approvals.jsonl`
- **Reports:** `~/.local/share/policy-scout/reports/`
- **Sandbox workspaces:** `~/.local/share/policy-scout/sandboxes/`
- **Sandbox results:** `~/.local/share/policy-scout/sandbox-results/`
- **Migrations:** `~/.local/share/policy-scout/migrations/`
- **Backups:** `~/.local/share/policy-scout/backups/`

### Override paths with environment variables

- `POLICY_SCOUT_AUDIT_DB_PATH` - SQLite database path
- `POLICY_SCOUT_AUDIT_PATH` - JSONL file path
- `POLICY_SCOUT_APPROVAL_PATH` - Approvals storage path
- `POLICY_SCOUT_REPORT_ROOT` - Reports directory path
- `POLICY_SCOUT_SANDBOX_ROOT` - Sandbox workspaces path
- `POLICY_SCOUT_SWEEP_ROOT` - Sweep outputs path
- `POLICY_SCOUT_MIGRATION_ROOT` - Migration backups path
- `POLICY_SCOUT_BACKUP_ROOT` - General backups path

### Empty states

On a fresh install with no data yet:
- `policy-scout doctor --json` will pass with a warning for report directory (not created until first report)
- `policy-scout audit stats --json` will return `{"total_events": 0, "by_type": {}}`
- `policy-scout audit list --json` will return an empty array `[]`
- `policy-scout report list --json` will return an error: "No Scout Reports found. Run a Policy Scout command with --report, sandbox, or sweep first."
- `policy-scout data status --json` will show zero counts for all categories

This is normal behavior. Generate safe demo data by running:
```bash
policy-scout check --json "git status"
policy-scout check --json "npm install left-pad"
policy-scout check --json "rm -rf /"
```

These check commands create audit events without executing any commands. After running checks, `policy-scout audit list --json` will show events and `policy-scout audit stats --json` will show counts.

---

## Green Checkpoint Commands

Run these commands from the repository root to verify a complete working setup:

```bash
# From repo root
cd /path/to/policy-scout

# Python/CLI verification
python -m pytest -q
PYTHONPATH=/path/to/policy-scout python -m policy_scout.cli.main doctor --json
PYTHONPATH=/path/to/policy-scout python -m policy_scout.cli.main eval run

# Desktop verification (if using desktop UI)
cd ui/desktop
npm run build

cd src-tauri
cargo check
cargo test
```

Expected results:
- pytest: 621 passed
- doctor: JSON output with all checks "ok"
- eval: 44/44 passed
- npm build: successful compilation
- cargo check: successful compilation
- cargo test: 18 passed

---

## Desktop Dogfood Checklist

Before trusting the desktop app, verify it through Policy Scout's own CLI checks:

```bash
# CLI verification
policy-scout doctor --json
policy-scout eval run
policy-scout check --json "git status"
policy-scout check --json "npm install left-pad"
policy-scout check --json "rm -rf /"

# Desktop build verification
cd ui/desktop
npm run build
cd src-tauri
cargo check
cargo test

# Native app verification
cd /path/to/policy-scout/ui/desktop
npm run tauri dev
```

In the native app:
- Verify Decision Check shows "NOT EXECUTED" on all results
- Verify Audit Events populates after check probes

---

## Native Smoke Checklist

For manual verification of the desktop UI, see the native smoke checklist:

`docs/compressed/TAURI_NATIVE_MANUAL_SMOKE_CHECKLIST_SOURCE.md`

This checklist verifies:
- Native window startup
- Live data loading
- Card rendering
- Safety boundary enforcement (no execution, no mutation, no approval, no deletion UI)
- Browser preview fallback behavior

---

## Safety Boundaries

### Desktop UI is read-only/check-only

The Tauri desktop UI is explicitly constrained to read-only display:
- No command execution UI
- No approval resolution UI
- No sandbox migration UI
- No cleanup deletion (dry-run preview only)
- No report/audit export or deletion UI
- No arbitrary shell access
- No direct SQLite or filesystem access from frontend

### Cleanup is dry-run only

The `policy-scout data cleanup` command is preview-only in v0.1:
- Reports planned items, estimated sizes, and warnings
- No deletion path exists
- No `--yes` flag exists
- High-risk targets (audit, reports, approvals, migrations, backups) are not supported

### Setup does not require risky commands

This guide does not ask you to:
- Run unknown install scripts
- Execute network-fetched code
- Modify system permissions
- Install untrusted packages

---

## Troubleshooting

### Python externally-managed error

If you see an error about externally-managed Python environments:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Tauri build fails on Linux

Install the required system dependencies:
```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
```

### pytest fails from subdirectory

Always run pytest from the repository root:
```bash
cd /path/to/policy-scout
python -m pytest
```

Some subprocess-based smoke tests inherit CWD and will fail if invoked from subdirectories.

### CLI not found after install

Ensure your virtual environment is activated:
```bash
source .venv/bin/activate
policy-scout doctor
```

Or use the module form:
```bash
PYTHONPATH=/path/to/policy-scout python -m policy_scout.cli.main doctor
```

---

## Known Limitations

- **Desktop UI:** Experimental v0.2.x read-only UI, not production-ready
- **Sandbox:** npm-only (pnpm/yarn/bun sandbox execution deferred)
- **Redaction:** Regex-based only, may miss novel secrets
- **Data cleanup:** Preview-only (no deletion path in v0.1)
- **Platform:** Linux-first for quick sweep and desktop UI

---

## Next Steps

After successful setup:
- Run `policy-scout demo` for a safe demo sequence
- Read `README.md` for usage examples
- See `docs/IMPLEMENTATION_STATUS.md` for implementation status
- See `ui/desktop/README.md` for desktop UI details
