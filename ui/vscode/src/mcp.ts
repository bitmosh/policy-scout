import * as fs from "fs/promises";
import * as path from "path";
import * as vscode from "vscode";

interface CursorMcpServer {
  command: string;
  args: string[];
  env: Record<string, string>;
}

interface CursorMcpConfig {
  mcpServers: Record<string, CursorMcpServer>;
}

export function isCursorHost(): boolean {
  return (
    !!process.env.CURSOR_CHANNEL ||
    vscode.env.appName.toLowerCase().includes("cursor")
  );
}

/**
 * Registers policy-scout as an MCP server in VS Code's language model / agent mode.
 * VS Code manages the process lifecycle; we just declare the server definition.
 * getExe is a closure so re-resolution after config changes is reflected automatically.
 */
export function registerMcpProvider(
  context: vscode.ExtensionContext,
  getExe: () => string | null
): void {
  const emitter = new vscode.EventEmitter<void>();

  const provider = vscode.lm.registerMcpServerDefinitionProvider(
    "policy-scout.mcp",
    {
      onDidChangeMcpServerDefinitions: emitter.event,

      provideMcpServerDefinitions: (_token: vscode.CancellationToken) => {
        const exe = getExe();
        if (!exe) return [];
        return [
          new vscode.McpStdioServerDefinition("Policy Scout", exe, ["serve", "--mcp"]),
        ];
      },
    }
  );

  context.subscriptions.push(provider, emitter);
}

/**
 * Writes the policy-scout MCP server entry into .cursor/mcp.json.
 * Merges with any existing entries — never overwrites a key the user has customised.
 * Called once at activation when running inside Cursor.
 */
export async function ensureCursorMcp(
  workspaceRoot: string,
  exe: string
): Promise<void> {
  const mcpPath = path.join(workspaceRoot, ".cursor", "mcp.json");
  let config: CursorMcpConfig = { mcpServers: {} };

  try {
    const raw = await fs.readFile(mcpPath, "utf8");
    const parsed = JSON.parse(raw) as Partial<CursorMcpConfig>;
    config.mcpServers = parsed.mcpServers ?? {};
  } catch {
    // File doesn't exist yet — start fresh
  }

  if (config.mcpServers["policy-scout"]) return;

  config.mcpServers["policy-scout"] = {
    command: exe,
    args: ["serve", "--mcp"],
    env: {},
  };

  await fs.mkdir(path.dirname(mcpPath), { recursive: true });
  await fs.writeFile(mcpPath, JSON.stringify(config, null, 2) + "\n", "utf8");
}
