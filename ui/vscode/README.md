# Policy Scout — VS Code / Cursor extension

**Status: experimental alpha — source only, not packaged or published**

Brings Policy Scout into VS Code and Cursor so sweep findings appear inline and
IDE agents can call policy checks in-loop before acting.

## What it does

### Sweep diagnostics

On save of `package.json`, lockfiles, GitHub Actions workflows, or shell scripts,
runs `policy-scout sweep project --json` and populates VS Code's Problems panel.
Critical and high findings appear as editor errors; medium as warnings. Can be
disabled via the `policy-scout.enableSweepOnSave` setting.

### Pre-commit hook management

Detects whether the pre-commit hook is installed and offers to install it via a
one-time notification. Install and uninstall are also available as VS Code
commands. The hook calls Policy Scout's staged-scan before each commit.

### MCP server registration

This is the in-loop enforcement path: IDE agents can call `policy_scout_check`
as a tool before executing shell commands.

- **VS Code** (agent mode): registers via `vscode.lm.registerMcpServerDefinitionProvider`.
  VS Code manages the server process lifecycle.
- **Cursor**: writes the server entry into `.cursor/mcp.json` on first activation.
  Merge-safe — existing entries are not overwritten.

### Binary resolution

Discovers the `policy-scout` binary via: configured path → login shell PATH
(handles pyenv, pipx, conda shims) → common install locations. Prompts to set
`policy-scout.executablePath` if the binary cannot be found.

## Building from source

```bash
cd ui/vscode
npm ci
npm run compile       # TypeScript → out/
```

To produce a `.vsix` for sideloading:

```bash
npx vsce package
```

Note: `vsce` is not installed by default. The compiled `out/` directory can be
loaded directly in VS Code extension development mode (`F5` from the extension
directory).

## Configuration

| Setting | Default | Description |
|---|---|---|
| `policy-scout.executablePath` | `""` | Explicit binary path; empty means auto-resolve |
| `policy-scout.enableSweepOnSave` | `false` | Run project sweep on save of trigger files |

## Limitations

- Not packaged, not in any marketplace.
- `vscode.lm.registerMcpServerDefinitionProvider` requires a recent VS Code build
  with agent mode; the API may not exist in older releases.
- Sweep-on-save trigger glob is hardcoded; project-specific exclusions are not yet
  configurable from the extension.
- No integration tests; behavior is manually verified.
