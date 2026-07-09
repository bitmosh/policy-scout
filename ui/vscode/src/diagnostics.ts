// SPDX-License-Identifier: Apache-2.0
import * as cp from "child_process";
import * as path from "path";
import * as vscode from "vscode";
import { updateStatusBar } from "./statusBar";

interface SweepFinding {
  severity?: string;
  confidence?: string;
  category?: string;
  title?: string;
  location?: string;
  why_it_matters?: string;
}

interface SweepResult {
  findings?: SweepFinding[];
}

const SWEEP_TRIGGER_GLOB =
  "{package.json,package-lock.json,.github/**/*.yml,.github/**/*.yaml,**/*.sh}";

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

function locationToRange(
  location: string,
  workspaceRoot: string
): { uri: vscode.Uri; range: vscode.Range } {
  const colonIdx = location.indexOf(":");
  const filePart = colonIdx >= 0 ? location.slice(0, colonIdx) : location;
  const restPart = colonIdx >= 0 ? location.slice(colonIdx + 1) : "";

  const uri = vscode.Uri.file(path.join(workspaceRoot, filePart || "."));
  const lineNum = /^\d+$/.test(restPart) ? Math.max(0, parseInt(restPart, 10) - 1) : 0;
  const range = new vscode.Range(lineNum, 0, lineNum, 0);

  return { uri, range };
}

function severityToDiagnosticSeverity(s: string): vscode.DiagnosticSeverity {
  switch (s.toLowerCase()) {
    case "critical":
    case "high":
      return vscode.DiagnosticSeverity.Error;
    case "medium":
      return vscode.DiagnosticSeverity.Warning;
    default:
      return vscode.DiagnosticSeverity.Information;
  }
}

function formatMessage(f: SweepFinding): string {
  const parts: string[] = [f.title ?? "Sweep finding"];
  if (f.confidence) parts.push(`[${f.confidence} confidence]`);
  if (f.why_it_matters) parts.push(`— ${f.why_it_matters}`);
  return parts.join(" ");
}

export async function runSweep(
  exe: string,
  workspaceRoot: string,
  collection: vscode.DiagnosticCollection,
  bar: vscode.StatusBarItem,
  mode: "project" | "quick"
): Promise<void> {
  updateStatusBar(bar, { loading: true, findingsCount: 0, error: false });
  collection.clear();

  const args = ["sweep", mode, "--json"];
  if (mode === "project") args.push("--project", workspaceRoot);

  try {
    const stdout = await spawnCollect(exe, args, workspaceRoot);
    const data: SweepResult = JSON.parse(stdout);
    const findings = data.findings ?? [];

    const byFile = new Map<string, vscode.Diagnostic[]>();

    for (const finding of findings) {
      const { uri, range } = locationToRange(finding.location ?? "", workspaceRoot);
      const severity = severityToDiagnosticSeverity(finding.severity ?? "");
      const diag = new vscode.Diagnostic(range, formatMessage(finding), severity);
      diag.source = "Policy Scout";
      if (finding.category) diag.code = finding.category;

      const key = uri.toString();
      if (!byFile.has(key)) byFile.set(key, []);
      byFile.get(key)!.push(diag);
    }

    for (const [uriStr, diags] of byFile) {
      collection.set(vscode.Uri.parse(uriStr), diags);
    }

    updateStatusBar(bar, { loading: false, findingsCount: findings.length, error: false });
  } catch (err) {
    updateStatusBar(bar, { loading: false, findingsCount: 0, error: true });
    void vscode.window.showErrorMessage(`Policy Scout sweep failed: ${err}`);
  }
}

export function registerSaveWatcher(
  context: vscode.ExtensionContext,
  getExe: () => string | null,
  getRoot: () => string | undefined,
  collection: vscode.DiagnosticCollection,
  bar: vscode.StatusBarItem
): void {
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (!vscode.workspace.getConfiguration("policy-scout").get<boolean>("enableSweepOnSave")) return;
      if (vscode.languages.match({ pattern: SWEEP_TRIGGER_GLOB }, doc) === 0) return;
      const exe = getExe();
      const root = getRoot();
      if (!exe || !root) return;
      void runSweep(exe, root, collection, bar, "project");
    })
  );
}
