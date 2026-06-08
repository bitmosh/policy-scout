# Policy Scout Tauri UI

Experimental read-only overview dashboard for Policy Scout.

## Development Modes

### Browser/Vite Preview (Static Layout Only)

```bash
npm run dev
```

- Opens a browser preview at http://localhost:1420
- Useful for checking static layout and styling
- **Cannot load live Policy Scout CLI data** (Tauri invoke APIs unavailable in browser context)
- Will show friendly message: "Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data."

### Native Tauri Runtime (Live Data)

```bash
npm run tauri dev
```

- Launches the native Tauri application window
- Required for live Doctor, Data, Reports, Audit, Cleanup, and Eval cards
- Uses Tauri invoke APIs to call Policy Scout CLI commands
- All data comes from the CLI (read-only, no mutations from UI)

### Build Checks

```bash
# Frontend build check
npm run build

# Rust backend compile check
cd src-tauri && cargo check
```

## Current Cards

- Doctor Status - Health diagnostics from `policy-scout doctor --json`
- Data Status - Local data status from `policy-scout data status --json`
- Reports List - Report list from `policy-scout report list --json --limit 5`
- Audit Stats - Audit statistics from `policy-scout audit stats --json`
- Cleanup Dry-Run - Cleanup preview from `policy-scout data cleanup --target <target> --dry-run --json`
- Eval Results - Eval suite summary from `policy-scout eval run --json`

## Security Boundaries

- Read-only UI - no command execution, approval, migration, or deletion from the UI
- No arbitrary shell access or frontend-provided argv arrays
- No direct SQLite or filesystem access from frontend
- CLI remains the authority - this is a preview interface only

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
