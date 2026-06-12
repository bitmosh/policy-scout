# Implementation Plan — Gap 14: Editor Integrations (VS Code / Cursor)

## Problem

Policy Scout has no editor presence. A developer running Cursor or VS Code has no inline
visibility into sweep findings, no automatic MCP tool registration for their AI agent,
and no friction-free path to install the pre-commit hook. The only way to interact with
policy-scout is to leave the editor and run CLI commands in a terminal.

The gap is especially felt in Cursor: agents in Cursor invoke shell commands and package
installs constantly. Without policy-scout registered as an MCP server, the agent bypasses
the policy engine entirely — the tool that's most valuable as an AI safety harness is
invisible to the AI.

## Goal

A single VS Code extension (`.vsix`) that works unchanged in both VS Code and Cursor.
Three capabilities in priority order:

1. **Sweep findings → Diagnostics panel.** `policy-scout sweep project` runs on demand
   and surfaces findings inline in the Problems panel, mapped to their source files.
2. **MCP server auto-registration.** The extension registers `policy-scout serve --mcp`
   with VS Code's agent mode (Copilot) and writes `.cursor/mcp.json` for Cursor, so the
   policy-scout tools are available to the AI without manual config.
3. **Git hook surface.** The extension detects whether the pre-commit hook is installed
   and offers a one-click install/uninstall notification.

Status bar, command palette entries, and a `policy-scout.executablePath` config setting
are cross-cutting concerns that all three capabilities share.

---

## Non-Goals

- No approval resolution UI in the extension (CLI remains the authority for approvals)
- No sandbox migration UI
- No cleanup or deletion actions
- No extension-managed policy editing
- No "run command through policy gate" terminal integration (deferred — requires terminal
  API complexity disproportionate to the value at this stage)
- No LSP server — direct CLI + JSON is sufficient; LSP adds complexity without benefit
  for this use case
- No Windows support in Phase 1 (PATH/venv resolution is platform-specific; Linux/macOS
  first, Windows as a follow-on)

---

## Repository Layout

The extension lives in a new top-level directory alongside `ui/desktop/`:

```
policy-scout/
├── ui/
│   ├── desktop/          # Tauri app (existing)
│   └── vscode/           # NEW — VS Code/Cursor extension
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/
│       │   ├── extension.ts          # activate() / deactivate()
│       │   ├── executable.ts         # binary resolution + version check
│       │   ├── diagnostics.ts        # sweep → DiagnosticCollection
│       │   ├── mcp.ts                # MCP server registration
│       │   ├── hooks.ts              # pre-commit hook detection + install
│       │   └── statusBar.ts          # status bar item
│       └── README.md
```

---

## Affected Files (new)

All files in `ui/vscode/` are new. No existing Python, Rust, or CLI code changes in
Phase 1–3. Phase 4 adds `--json` output to `policy-scout hooks status` if it doesn't
already exist.

---

## Implementation Approach

---

### Phase 1 — Skeleton, binary resolution, status bar

**Goal:** Extension activates, finds the `policy-scout` binary, shows a status bar item.
No sweep or MCP yet. This phase proves the scaffolding before adding real behaviour.

#### `package.json` (extension manifest)

```json
{
  "name": "policy-scout",
  "displayName": "Policy Scout",
  "description": "Local command safety harness — sweep findings, MCP tools, pre-commit hooks",
  "version": "0.1.0",
  "engines": { "vscode": "^1.85.0" },
  "categories": ["Linters", "Other"],
  "activationEvents": ["onStartupFinished"],
  "main": "./out/extension.js",
  "contributes": {
    "configuration": {
      "title": "Policy Scout",
      "properties": {
        "policy-scout.executablePath": {
          "type": "string",
          "default": "",
          "description": "Path to the policy-scout executable. Leave empty to search PATH."
        },
        "policy-scout.enableSweepOnSave": {
          "type": "boolean",
          "default": false,
          "description": "Run a project sweep when package.json or workflow files are saved."
        }
      }
    },
    "commands": [
      { "command": "policy-scout.runSweep",        "title": "Policy Scout: Run Project Sweep" },
      { "command": "policy-scout.runQuickSweep",   "title": "Policy Scout: Run Quick Sweep" },
      { "command": "policy-scout.showFindings",    "title": "Policy Scout: Show Findings" },
      { "command": "policy-scout.installHook",     "title": "Policy Scout: Install Pre-commit Hook" },
      { "command": "policy-scout.uninstallHook",   "title": "Policy Scout: Uninstall Pre-commit Hook" }
    ],
    "mcpServerDefinitionProviders": [
      { "id": "policy-scout.mcp", "label": "Policy Scout" }
    ]
  }
}
```

#### `executable.ts` — binary resolution

This is the most failure-prone part of any CLI extension. Resolve in order:

1. `policy-scout.executablePath` setting (user-configured absolute path)
2. `which policy-scout` / `where policy-scout` via a login shell
3. Common install locations: `~/.local/bin/policy-scout`, `~/.cargo/bin/policy-scout`,
   `$(pipx environment --value PIPX_LOCAL_VENVS)/policy-scout/bin/policy-scout`

```typescript
export async function resolveExecutable(): Promise<string | null> {
  const configured = vscode.workspace
    .getConfiguration('policy-scout')
    .get<string>('executablePath', '');
  if (configured) return configured;

  // Try shell PATH (handles pyenv, nvm, pipx shims)
  try {
    const result = await runShell('which policy-scout');
    if (result.trim()) return result.trim();
  } catch { /* not found in PATH */ }

  // Fallback: common locations
  const candidates = [
    path.join(os.homedir(), '.local', 'bin', 'policy-scout'),
    path.join(os.homedir(), '.cargo', 'bin', 'policy-scout'),
  ];
  for (const c of candidates) {
    if (await fileExists(c)) return c;
  }
  return null;
}
```

If resolution fails, show a one-time notification:

```
Policy Scout binary not found. Set "policy-scout.executablePath" in settings, or
install with: pip install policy-scout
```

with a **Configure** button that opens settings to that key.

After resolving, verify the version:

```typescript
// policy-scout --version must return something parseable
const { stdout } = await exec(`${exe} --version`);
// log to output channel; warn if version is below minimum supported
```

#### `statusBar.ts`

```typescript
export function createStatusBar(context: vscode.ExtensionContext): vscode.StatusBarItem {
  const bar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
  bar.text = '$(shield) Policy Scout';
  bar.tooltip = 'Policy Scout — click to run sweep';
  bar.command = 'policy-scout.runSweep';
  bar.show();
  context.subscriptions.push(bar);
  return bar;
}

export function updateStatusBar(bar: vscode.StatusBarItem, state: BarState) {
  if (state.loading) {
    bar.text = '$(loading~spin) Policy Scout';
    bar.backgroundColor = undefined;
  } else if (state.error) {
    bar.text = '$(shield) Policy Scout: error';
    bar.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
  } else if (state.findingsCount > 0) {
    bar.text = `$(shield) Policy Scout: ${state.findingsCount} finding${state.findingsCount === 1 ? '' : 's'}`;
    bar.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    bar.command = 'policy-scout.showFindings';
  } else {
    bar.text = '$(shield) Policy Scout: clean';
    bar.backgroundColor = undefined;
    bar.command = 'policy-scout.runSweep';
  }
}
```

**STOP gate:** Extension activates in VS Code and Cursor. Status bar shows. Notification
fires when binary is missing. `policy-scout --version` output appears in the Output panel.

---

### Phase 2 — Sweep → Diagnostics

**Goal:** Running the sweep command populates the Problems panel with findings mapped to
their source files.

#### Location parsing

`SweepFinding.location` is a string like:
- `"package.json:scripts.postinstall"`
- `"package.json"` (file-only)
- `".github/workflows/ci.yml:jobs.build.steps[2]"`
- `"src/index.js:42"` (file:line when available)

Parse strategy:

```typescript
function locationToRange(location: string, workspaceRoot: string): {
  uri: vscode.Uri;
  range: vscode.Range;
} {
  // Split on first colon that's followed by a digit (line number) or a path key
  const colonIdx = location.indexOf(':');
  const filePart  = colonIdx >= 0 ? location.slice(0, colonIdx) : location;
  const restPart  = colonIdx >= 0 ? location.slice(colonIdx + 1) : '';

  const uri = vscode.Uri.file(path.join(workspaceRoot, filePart));

  // If rest is a bare line number, use it; otherwise pin to line 0
  const lineNum = /^\d+$/.test(restPart) ? Math.max(0, parseInt(restPart) - 1) : 0;
  const range = new vscode.Range(lineNum, 0, lineNum, 0);

  return { uri, range };
}
```

File-level findings (no line info) are pinned to line 0. This is honest — the finding is
real but the exact line is unknown. Inline squiggles at line 0 are less noisy than
fabricated positions.

#### `diagnostics.ts`

```typescript
export async function runSweep(
  exe: string,
  workspaceRoot: string,
  collection: vscode.DiagnosticCollection,
  bar: vscode.StatusBarItem,
  mode: 'project' | 'quick'
): Promise<void> {
  updateStatusBar(bar, { loading: true, findingsCount: 0, error: false });
  collection.clear();

  const args = ['sweep', mode, '--json'];
  if (mode === 'project') args.push('--project', workspaceRoot);

  try {
    const { stdout } = await spawnJson(exe, args);
    const data: SweepData = JSON.parse(stdout);

    const byFile = new Map<string, vscode.Diagnostic[]>();

    for (const finding of data.findings ?? []) {
      const { uri, range } = locationToRange(finding.location ?? '', workspaceRoot);
      const severity = severityToDiagnosticSeverity(finding.severity ?? '');
      const diag = new vscode.Diagnostic(range, formatMessage(finding), severity);
      diag.source = 'Policy Scout';
      diag.code = finding.category ?? undefined;

      const key = uri.toString();
      if (!byFile.has(key)) byFile.set(key, []);
      byFile.get(key)!.push(diag);
    }

    for (const [uriStr, diags] of byFile) {
      collection.set(vscode.Uri.parse(uriStr), diags);
    }

    updateStatusBar(bar, { loading: false, findingsCount: data.findings?.length ?? 0, error: false });
  } catch (e) {
    updateStatusBar(bar, { loading: false, findingsCount: 0, error: true });
    vscode.window.showErrorMessage(`Policy Scout sweep failed: ${e}`);
  }
}

function severityToDiagnosticSeverity(s: string): vscode.DiagnosticSeverity {
  switch (s.toLowerCase()) {
    case 'critical':
    case 'high':   return vscode.DiagnosticSeverity.Error;
    case 'medium': return vscode.DiagnosticSeverity.Warning;
    default:       return vscode.DiagnosticSeverity.Information;
  }
}

function formatMessage(f: SweepFinding): string {
  const parts = [f.title ?? 'Sweep finding'];
  if (f.confidence) parts.push(`[${f.confidence} confidence]`);
  if (f.why_it_matters) parts.push(`— ${f.why_it_matters}`);
  return parts.join(' ');
}
```

#### Optional on-save trigger

When `policy-scout.enableSweepOnSave` is true, watch for saves of files the sweep engine
cares about: `package.json`, `*.yaml`/`*.yml` in `.github/`, shell scripts. Don't re-run
the full sweep on every `.ts` save — that's too slow.

```typescript
const SWEEP_TRIGGER_GLOB = '{package.json,package-lock.json,.github/**/*.yml,.github/**/*.yaml,**/*.sh}';

vscode.workspace.onDidSaveTextDocument((doc) => {
  if (!vscode.workspace.getConfiguration('policy-scout').get('enableSweepOnSave')) return;
  if (vscode.languages.match({ pattern: SWEEP_TRIGGER_GLOB }, doc) > 0) {
    runSweep(exe, workspaceRoot, collection, bar, 'project');
  }
});
```

**STOP gate:** Running "Policy Scout: Run Project Sweep" from the Command Palette populates
the Problems panel. Clicking a finding navigates to the file. Status bar shows the finding
count. Running with no findings shows "clean".

---

### Phase 3 — MCP server registration

**Goal:** Copilot/agent mode in VS Code and AI agents in Cursor get the five
`policy_scout_*` MCP tools without any manual configuration.

#### VS Code (`mcp.ts`)

VS Code's `vscode.lm.registerMcpServerDefinitionProvider` API manages the process
lifecycle. The extension declares the server definition; VS Code starts and stops
`policy-scout serve --mcp` as needed.

```typescript
export function registerMcpProvider(
  context: vscode.ExtensionContext,
  exe: string
): void {
  const emitter = new vscode.EventEmitter<void>();

  const provider = vscode.lm.registerMcpServerDefinitionProvider(
    'policy-scout.mcp',
    {
      onDidChangeMcpServerDefinitions: emitter.event,
      provideMcpServerDefinitions: async () => [
        new vscode.McpStdioServerDefinition(
          'Policy Scout',
          exe,
          ['serve', '--mcp'],
          {},          // env — inherit from host
        )
      ],
      resolveMcpServerDefinition: async (server) => server,
    }
  );

  context.subscriptions.push(provider, emitter);
}
```

The `mcpServerDefinitionProviders` contribution in `package.json` declares the provider
ID so VS Code knows to call it during agent mode initialization.

#### Cursor (`.cursor/mcp.json` write)

Cursor does not use the VS Code MCP provider API. The extension writes the server entry
into the workspace `.cursor/mcp.json` file instead. This is done once at activation,
merging with any existing entries rather than overwriting.

```typescript
export async function ensureCursorMcp(
  workspaceRoot: string,
  exe: string
): Promise<void> {
  const mcpPath = path.join(workspaceRoot, '.cursor', 'mcp.json');
  let config: CursorMcpConfig = { mcpServers: {} };

  try {
    const raw = await fs.readFile(mcpPath, 'utf8');
    config = JSON.parse(raw);
  } catch { /* file doesn't exist yet */ }

  // Merge — don't overwrite an entry the user may have customised
  if (!config.mcpServers['policy-scout']) {
    config.mcpServers['policy-scout'] = {
      command: exe,
      args: ['serve', '--mcp'],
      env: {},
    };
    await fs.mkdir(path.dirname(mcpPath), { recursive: true });
    await fs.writeFile(mcpPath, JSON.stringify(config, null, 2), 'utf8');
  }
}
```

Detect Cursor vs VS Code at runtime:

```typescript
// Cursor sets this env var in its extension host
const isCursor = !!process.env.CURSOR_CHANNEL || vscode.env.appName.toLowerCase().includes('cursor');

if (isCursor) {
  await ensureCursorMcp(workspaceRoot, exe);
} else {
  registerMcpProvider(context, exe);
}
```

**STOP gate (VS Code):** `policy_scout_check`, `policy_scout_sweep`, and the other three
tools appear in the Copilot agent tool list. Calling `policy_scout_check` with a test
command returns a structured decision.

**STOP gate (Cursor):** `.cursor/mcp.json` is written to the workspace root. Restarting
Cursor's MCP service surfaces the policy-scout tools in the agent.

---

### Phase 4 — Git hook surface

**Goal:** Extension detects pre-commit hook installation status and offers one-click
install/uninstall.

#### CLI prerequisite

`policy-scout hooks status --json` must return a machine-readable result. Check whether
this exists; if not, add it alongside this phase (small CLI-only change, no new modules).

Expected JSON shape:

```json
{
  "hooks": [
    { "name": "pre-commit", "installed": true, "managed": true, "path": ".git/hooks/pre-commit" }
  ]
}
```

#### `hooks.ts`

```typescript
export async function checkHookStatus(exe: string, workspaceRoot: string): Promise<HookStatus[]> {
  const { stdout } = await spawnJson(exe, ['hooks', 'status', '--json'], { cwd: workspaceRoot });
  const data = JSON.parse(stdout);
  return data.hooks ?? [];
}

export async function showHookNotification(
  exe: string,
  workspaceRoot: string
): Promise<void> {
  const hooks = await checkHookStatus(exe, workspaceRoot);
  const preCommit = hooks.find((h) => h.name === 'pre-commit');

  if (!preCommit?.installed) {
    const choice = await vscode.window.showInformationMessage(
      'Policy Scout: pre-commit hook is not installed. Install it to scan staged files before each commit.',
      'Install',
      'Dismiss'
    );
    if (choice === 'Install') {
      await spawnJson(exe, ['hooks', 'install'], { cwd: workspaceRoot });
      vscode.window.showInformationMessage('Policy Scout: pre-commit hook installed.');
    }
  }
}
```

Show the notification once per workspace session (not on every activation). Track via
`context.workspaceState.get('hookNotificationDismissed')`.

**STOP gate:** Opening a workspace without the hook installed shows the notification once.
Clicking Install runs `hooks install`. Reopening the workspace does not show the
notification again.

---

## Integration Points with Existing Policy Scout

| Extension feature | Policy Scout CLI command | Notes |
|---|---|---|
| Project sweep | `policy-scout sweep project --json --project <root>` | Returns `SweepData`; findings have `location`, `severity`, `confidence`, `title` |
| Quick sweep | `policy-scout sweep quick --json` | Same shape, no `--project` arg |
| MCP server | `policy-scout serve --mcp` | stdio JSON-RPC 2.0; managed by VS Code or as a subprocess |
| Hook status | `policy-scout hooks status --json` | May need `--json` flag adding (Phase 4 prereq) |
| Hook install | `policy-scout hooks install` | Already implemented in `git/hooks.py` |
| Version check | `policy-scout --version` | Used at activation to validate binary |

No changes to the Python CLI are needed for Phases 1–3. Phase 4 may need a `--json` flag
on `hooks status` if it doesn't exist.

---

## Open Questions

| Question | Impact |
|---|---|
| Does `policy-scout hooks status --json` exist? | Phase 4 prereq — check before starting |
| Should `.cursor/mcp.json` be committed to the repo? | Policy decision: it's a dev tool config; probably yes for teams, but a single-dev repo may want it in `.gitignore` |
| Extension marketplace target: Open VSX only, or also Microsoft Marketplace? | Microsoft Marketplace requires a publisher account and a PAT; Open VSX is simpler and covers Cursor. Recommend Open VSX first. |
| Minimum VS Code version? | `vscode.lm.registerMcpServerDefinitionProvider` landed in VS Code 1.99 (April 2025). `engines.vscode` should be `^1.99.0` for MCP support. Phase 1–2 work on 1.85+. |
| Should sweep findings persist across reloads (workspace state)? | Probably not — stale findings are worse than no findings. Re-run on activation if `enableSweepOnSave` is on. |

---

## Test Strategy

### Unit tests (Jest / vitest)

- `executable.ts`: mock `which`, test resolution order, test missing-binary notification
- `diagnostics.ts`: test `locationToRange` with file-only, file:line, and YAML-path formats; test `severityToDiagnosticSeverity` mapping
- `hooks.ts`: test notification suppression after dismissal

### Integration tests (VS Code extension test runner)

- Activate extension in a temp workspace containing a mock `package.json` with a
  suspicious `postinstall` script
- Run `policy-scout.runSweep` — verify `DiagnosticCollection` has entries
- Verify status bar text updates to show finding count

### Manual smoke checklist

- Binary not found → notification with Configure button
- Binary found, no findings → "clean" in status bar
- Binary found, findings → Problems panel populated, click navigates to file
- MCP provider registered → tools appear in Copilot tool list
- Cursor: `.cursor/mcp.json` written correctly, tools available in agent

---

## Effort Estimate

| Phase | Description | Estimated lines |
|---|---|---|
| 1 | Skeleton, binary resolution, status bar | ~250 |
| 2 | Sweep → diagnostics | ~300 |
| 3 | MCP registration (VS Code + Cursor) | ~150 |
| 4 | Git hook surface | ~150 |
| **Total** | | **~850** |

All TypeScript. No new Python. No new Rust.

---

## Dependency Notes

The extension needs no npm packages beyond the VS Code API types (`@types/vscode`) and
the build toolchain (`esbuild` or `vite` + `tsc`). No new runtime dependencies — `child_process`
is Node built-in. Per the project's supply-chain policy, any dependency additions require
explicit manual approval before install.

---

## Implementation Sequence

1. `ui/vscode/` directory + `package.json` + `tsconfig.json` skeleton
2. Phase 1: `executable.ts` + `statusBar.ts` + `extension.ts` (activate/deactivate)
3. Verify activation in VS Code and Cursor before continuing
4. Phase 2: `diagnostics.ts` + sweep commands
5. Phase 3: `mcp.ts` + Cursor config write
6. Phase 4: `hooks.ts` + CLI `--json` flag if needed
7. Publish to Open VSX
