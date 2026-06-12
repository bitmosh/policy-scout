import * as cp from "child_process";
import * as vscode from "vscode";

interface HookStatus {
  name: string;
  installed: boolean;
  path: string | null;
  managed: boolean;
}

interface HooksReport {
  repo_root: string;
  hooks_dir: string;
  hooks: HookStatus[];
}

const DISMISSED_KEY = "hookNotificationDismissed";

function spawnCollect(exe: string, args: string[], cwd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = cp.spawn(exe, args, { cwd });
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
    proc.on("close", (code) => {
      if (code !== 0) reject(new Error(stderr.trim() || `Process exited with code ${code}`));
      else resolve(stdout);
    });
    proc.on("error", reject);
  });
}

async function checkHookStatus(exe: string, workspaceRoot: string): Promise<HookStatus[]> {
  const stdout = await spawnCollect(
    exe, ["git", "hooks", "status", "--json"], workspaceRoot
  );
  const report = JSON.parse(stdout) as HooksReport;
  return report.hooks ?? [];
}

export async function runHookInstall(exe: string, workspaceRoot: string): Promise<void> {
  await spawnCollect(exe, ["git", "hooks", "install"], workspaceRoot);
}

export async function runHookUninstall(exe: string, workspaceRoot: string): Promise<void> {
  await spawnCollect(exe, ["git", "hooks", "uninstall"], workspaceRoot);
}

/**
 * Shows a one-time notification when the pre-commit hook is not installed.
 * Suppressed permanently for this workspace once the user acts or dismisses.
 * Clearing workspaceState DISMISSED_KEY resets it (done by the uninstall command).
 */
export async function showHookNotification(
  exe: string,
  workspaceRoot: string,
  context: vscode.ExtensionContext
): Promise<void> {
  if (context.workspaceState.get<boolean>(DISMISSED_KEY)) return;

  let hooks: HookStatus[];
  try {
    hooks = await checkHookStatus(exe, workspaceRoot);
  } catch {
    return; // Not a git repo, binary error, or hooks dir missing — skip silently
  }

  const preCommit = hooks.find((h) => h.name === "pre-commit");
  if (preCommit?.installed) return;

  const choice = await vscode.window.showInformationMessage(
    "Policy Scout: The pre-commit hook is not installed. Install it to scan staged files before each commit.",
    "Install",
    "Dismiss"
  );

  if (choice === "Install") {
    try {
      await runHookInstall(exe, workspaceRoot);
      vscode.window.showInformationMessage("Policy Scout: Pre-commit hook installed.");
    } catch (err) {
      vscode.window.showErrorMessage(`Policy Scout: Hook install failed — ${err}`);
    }
  }

  // Suppress for this workspace regardless of choice made
  void context.workspaceState.update(DISMISSED_KEY, true);
}

export { DISMISSED_KEY };
