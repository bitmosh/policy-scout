# Installation and development

Policy Scout v0.3.9 is installed from source. It is not published to PyPI and
does not currently ship a desktop installer.

## Requirements

Core CLI:

- Python 3.12 or newer;
- Git;
- Rust stable to build the vendored Fossic PyO3 extension.

Optional workflows require their own host tools:

- npm, pnpm, yarn, or bun for real package review;
- `ss` or `netstat` and `ps` for portions of quick sweep;
- Git for history/staged integration;
- Linux `unshare`, optionally `strace` and OverlayFS support, for `sandbox-run`;
- Node.js 22, Rust stable, and WebKit/GTK libraries for the Tauri desktop.

## CLI setup

```bash
git clone <repository-url>
cd policy-scout

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install ./vendor/fossic/fossic-py
python -m pip install -e ".[dev]"
```

Policy Scout declares PyYAML as its direct runtime dependency. Fossic 1.8.1 is
vendored under `vendor/fossic/` and installed from that local source before
Policy Scout. Building it may download ordinary Maturin/Cargo build dependencies,
but it does not clone or import the upstream Fossic repository. The development
extra installs pytest. `jsonschema` is optional; contract tests skip schema
validation when unavailable.

## Verify the installation

```bash
policy-scout --help
policy-scout doctor --json
policy-scout eval run
python -m pytest -q
```

At the 2026-06-30 verification point, the repository produced 44/44 eval passes
and 1,150 Python test passes with 2 environment-dependent skips. Treat this as a
dated baseline, not a hard-coded expected count.

## Safe first commands

```bash
policy-scout demo
policy-scout check -- ls
policy-scout check -- npm install lodash
policy-scout policy show
policy-scout data status
```

`demo` and `check` do not execute submitted command text. The demo creates a
temporary workspace for inspection.

## Local state

Default durable state is under `~/.local/share/policy-scout/`:

```text
audit.db
audit.jsonl
approvals.jsonl
fossic.db
reports/
sandboxes/
sweeps/
migrations/
backups/
```

Some directories are created lazily. An empty report list on a fresh install is
normal.

## Isolated state

Tests and disposable manual checks should never use the real user data directory.
Override the relevant paths:

```bash
export POLICY_SCOUT_AUDIT_DB_PATH=/tmp/policy-scout-test/audit.db
export POLICY_SCOUT_AUDIT_PATH=/tmp/policy-scout-test/audit.jsonl
export POLICY_SCOUT_APPROVAL_PATH=/tmp/policy-scout-test/approvals.jsonl
export POLICY_SCOUT_REPORT_ROOT=/tmp/policy-scout-test/reports
export POLICY_SCOUT_SANDBOX_ROOT=/tmp/policy-scout-test/sandboxes
export POLICY_SCOUT_SWEEP_ROOT=/tmp/policy-scout-test/sweeps
export POLICY_SCOUT_MIGRATION_ROOT=/tmp/policy-scout-test/migrations
export POLICY_SCOUT_BACKUP_ROOT=/tmp/policy-scout-test/backups
export POLICY_SCOUT_FOSSIC_DB_PATH=/tmp/policy-scout-test/fossic.db
```

`POLICY_SCOUT_EVAL_CASES_PATH` selects an alternate eval YAML file.

## Running from a checkout

After editable installation, prefer the console script. From the repository root,
module invocation also works:

```bash
policy-scout doctor
python -m policy_scout.cli.main doctor
```

Subprocess tests intentionally set `PYTHONPATH` so they import this checkout.
Run the full suite from the repository root because smoke tests inherit their
working directory.

## Desktop development

The desktop is an optional Tauri companion whose backend invokes the installed
CLI.

```bash
cd ui/desktop
npm ci
npm run build

cd src-tauri
cargo check
cargo test
```

For live native data:

```bash
cd ui/desktop
npm run tauri dev
```

Browser preview uses mock data and cannot validate native CLI invocation.

Typical Debian/Ubuntu native dependencies include
`libwebkit2gtk-4.1-dev`, `libappindicator3-dev`, `librsvg2-dev`, and `patchelf`.
Package names vary by distribution.

## CI

`.github/workflows/ci.yml` has two jobs:

- Python 3.12: editable install, doctor, eval, and pytest;
- desktop: Node 22 frontend build plus Rust `cargo check` and `cargo test`.

CI does not build a packaged Tauri installer or perform native click-level UI
testing.

## Troubleshooting

### Vendored Fossic build fails

Confirm Rust stable is installed and run the local install from the repository
root: `python -m pip install ./vendor/fossic/fossic-py`. No upstream Fossic
checkout is required.

### Package sandbox command is unavailable

Install the requested package manager separately. Policy Scout does not install
npm, pnpm, yarn, or bun for you.

### General sandbox prerequisites fail

Run `policy-scout sandbox-check-prereqs --json`. Linux distributions and
containerized development environments commonly disable required namespace or
mount features.

### Tests fail from a subdirectory

Return to the repository root and run `python -m pytest`.
