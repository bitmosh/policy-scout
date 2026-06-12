import * as vscode from "vscode";
import { resolveExecutable } from "./executable";
import { runSweep, registerSaveWatcher } from "./diagnostics";
import { isCursorHost, registerMcpProvider, ensureCursorMcp } from "./mcp";
import { createStatusBar, updateStatusBar } from "./statusBar";

let outputChannel: vscode.OutputChannel;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  outputChannel = vscode.window.createOutputChannel("Policy Scout");
  context.subscriptions.push(outputChannel);

  outputChannel.appendLine("[policy-scout] activating...");

  let exe: string | null = await resolveExecutable(outputChannel);

  if (!exe) {
    void promptInstall();
  } else {
    outputChannel.appendLine(`[policy-scout] ready — binary: ${exe}`);
  }

  const bar = createStatusBar(context);
  updateStatusBar(bar, { loading: false, findingsCount: 0, error: !exe });

  const collection = vscode.languages.createDiagnosticCollection("policy-scout");
  context.subscriptions.push(collection);

  function workspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  function requireExeAndRoot(
    action: (exe: string, root: string) => void
  ): void {
    if (!exe) { void promptInstall(); return; }
    const root = workspaceRoot();
    if (!root) {
      vscode.window.showWarningMessage("Policy Scout: No workspace folder open.");
      return;
    }
    action(exe, root);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("policy-scout.showFindings", () => {
      void vscode.commands.executeCommand("workbench.action.problems.focus");
    }),

    vscode.commands.registerCommand("policy-scout.runSweep", () => {
      requireExeAndRoot((e, root) => {
        void runSweep(e, root, collection, bar, "project");
      });
    }),

    vscode.commands.registerCommand("policy-scout.runQuickSweep", () => {
      requireExeAndRoot((e, root) => {
        void runSweep(e, root, collection, bar, "quick");
      });
    }),

    vscode.commands.registerCommand("policy-scout.installHook", () => {
      if (!exe) { void promptInstall(); return; }
      vscode.window.showInformationMessage("Policy Scout: Hook management — coming in Phase 4.");
    }),

    vscode.commands.registerCommand("policy-scout.uninstallHook", () => {
      if (!exe) { void promptInstall(); return; }
      vscode.window.showInformationMessage("Policy Scout: Hook management — coming in Phase 4.");
    }),

    vscode.workspace.onDidChangeConfiguration(async (e: vscode.ConfigurationChangeEvent) => {
      if (!e.affectsConfiguration("policy-scout.executablePath")) return;
      exe = await resolveExecutable(outputChannel);
      updateStatusBar(bar, { loading: false, findingsCount: 0, error: !exe });
      if (exe) {
        outputChannel.appendLine(`[policy-scout] binary updated: ${exe}`);
      }
    })
  );

  registerSaveWatcher(context, () => exe, workspaceRoot, collection, bar);

  if (exe) {
    if (isCursorHost()) {
      const root = workspaceRoot();
      if (root) void ensureCursorMcp(root, exe);
    } else {
      registerMcpProvider(context, () => exe);
    }
  }

  outputChannel.appendLine("[policy-scout] activated.");
}

export function deactivate(): void {
  // subscriptions are disposed automatically by VS Code
}

async function promptInstall(): Promise<void> {
  const choice = await vscode.window.showWarningMessage(
    "Policy Scout: binary not found. Install with `pip install policy-scout` or set the executablePath in settings.",
    "Open Settings"
  );
  if (choice === "Open Settings") {
    void vscode.commands.executeCommand(
      "workbench.action.openSettings",
      "policy-scout.executablePath"
    );
  }
}
