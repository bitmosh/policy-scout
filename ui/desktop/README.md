# Policy Scout desktop

The desktop app is an experimental Tauri companion for Policy Scout v0.3.9.
The Python CLI remains authoritative for policy, execution, audit, reports, and
machine-readable contracts.

## Boundary

The desktop can inspect local state, trigger read/check operations, and display
evidence. It does not expose general command execution, approval resolution,
sandbox migration, arbitrary argv, direct SQLite access, or filesystem browsing.

Decision Check invokes `policy-scout check --json`; submitted command text is not
executed. The cleanup card is designed as preview-only, but its Rust wrapper still
sends a legacy `--dry-run` flag that the v0.3.9 CLI does not define.

## Data flow

```text
React card -> typed Tauri invoke -> Rust validation -> policy-scout CLI --json
                                                    -> parsed response envelope
```

Rust validates IDs, event types, cleanup targets, limits, offsets, and command
text before constructing CLI arguments. The frontend cannot supply a raw argv
array.

## Current surfaces

- health and local-data status;
- command Decision Check;
- report and sandbox-result lists/details;
- audit statistics, lists, filters, and details;
- eval results;
- quick and project sweeps;
- policy overview and validation;
- temporary-data cleanup preview.

Report, audit, and sandbox lists support bounded pagination. Findings are
previewed with explicit counts; the CLI remains the complete evidence surface.

## Contract discipline

Dashboard-consumed JSON shapes have:

- schemas under `src/contracts/`;
- domain TypeScript types under `src/types/`;
- browser mock fixtures under `src/mocks/`;
- live-output and fixture checks in `tests/test_json_contracts.py`;
- Rust tests for adapter validation and allowlists.

The schema checks are conditional on the optional Python `jsonschema` package.

## Development

From `ui/desktop/`:

```bash
npm ci
npm run build
npm run dev
```

`npm run dev` is a browser preview backed by mocks. It cannot validate Tauri
invocation.

For live CLI data:

```bash
npm run tauri dev
```

Rust verification:

```bash
cd src-tauri
cargo check
cargo test
```

See [project installation](../../docs/INSTALL.md) for Python, Node, Rust, and
Linux WebKit prerequisites.

## Known limitations

- Native click-level behavior is manually verified; CI compiles and unit-tests
  the frontend/Rust layers but does not automate a native window.
- There is no packaged installer.
- Browser preview cannot load live CLI data.
- Project sweep uses the Policy Scout process working directory; there is no
  project chooser.
- The cleanup card has CLI-argument drift (`--dry-run`) and needs correction.
- The dashboard is not a complete replacement for CLI evidence or administration.
