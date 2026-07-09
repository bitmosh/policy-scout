// SPDX-License-Identifier: Apache-2.0
import * as cp from "child_process";
import * as fs from "fs/promises";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

function runShell(cmd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    cp.exec(cmd, { shell: "/bin/bash", env: { ...process.env, BASH_ENV: undefined } }, (err, stdout) => {
      if (err) reject(err);
      else resolve(stdout);
    });
  });
}

async function fileExists(p: string): Promise<boolean> {
  try {
    await fs.access(p, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

/**
 * Resolves the policy-scout binary in this order:
 * 1. policy-scout.executablePath config setting
 * 2. Login shell PATH (handles pyenv, pipx, nvm shims)
 * 3. Common install locations ($HOME/.local/bin, pipx venv)
 */
export async function resolveExecutable(output: vscode.OutputChannel): Promise<string | null> {
  const configured = vscode.workspace
    .getConfiguration("policy-scout")
    .get<string>("executablePath", "")
    .trim();

  if (configured) {
    output.appendLine(`[policy-scout] configured path: ${configured}`);
    if (await fileExists(configured)) return configured;
    output.appendLine(`[policy-scout] configured path not found or not executable: ${configured}`);
  }

  // Login shell PATH — picks up pyenv, pipx, conda, nvm shims
  try {
    const which = await runShell("bash -lc 'which policy-scout'");
    const trimmed = which.trim();
    if (trimmed && (await fileExists(trimmed))) {
      output.appendLine(`[policy-scout] found via shell PATH: ${trimmed}`);
      return trimmed;
    }
  } catch {
    output.appendLine("[policy-scout] not found in shell PATH");
  }

  // Common install locations
  const home = os.homedir();
  const candidates: string[] = [
    path.join(home, ".local", "bin", "policy-scout"),
    path.join(home, ".cargo", "bin", "policy-scout"),
  ];

  try {
    const pipxHome = await runShell("bash -lc 'pipx environment --value PIPX_LOCAL_VENVS'");
    candidates.push(path.join(pipxHome.trim(), "policy-scout", "bin", "policy-scout"));
  } catch {
    // pipx not installed or PIPX_LOCAL_VENVS unavailable
  }

  for (const candidate of candidates) {
    if (await fileExists(candidate)) {
      output.appendLine(`[policy-scout] found at: ${candidate}`);
      return candidate;
    }
  }

  output.appendLine("[policy-scout] binary not found in any location");
  return null;
}
