// SPDX-License-Identifier: Apache-2.0
import * as vscode from "vscode";

export interface BarState {
  loading: boolean;
  findingsCount: number;
  error: boolean;
}

export function createStatusBar(context: vscode.ExtensionContext): vscode.StatusBarItem {
  const bar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
  bar.command = "policy-scout.runSweep";
  bar.tooltip = "Policy Scout — click to run sweep";
  context.subscriptions.push(bar);
  return bar;
}

export function updateStatusBar(bar: vscode.StatusBarItem, state: BarState): void {
  if (state.loading) {
    bar.text = "$(loading~spin) Policy Scout";
    bar.backgroundColor = undefined;
    bar.command = undefined;
  } else if (state.error) {
    bar.text = "$(shield) Policy Scout: error";
    bar.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
    bar.command = "policy-scout.showFindings";
  } else if (state.findingsCount > 0) {
    const s = state.findingsCount === 1 ? "" : "s";
    bar.text = `$(shield) Policy Scout: ${state.findingsCount} finding${s}`;
    bar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
    bar.command = "policy-scout.showFindings";
  } else {
    bar.text = "$(shield) Policy Scout: clean";
    bar.backgroundColor = undefined;
    bar.command = "policy-scout.runSweep";
  }
  bar.show();
}
