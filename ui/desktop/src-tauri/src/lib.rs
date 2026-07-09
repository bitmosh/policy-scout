// SPDX-License-Identifier: Apache-2.0
use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Serialize, Deserialize)]
struct CliJsonResponse {
    ok: bool,
    exit_code: i32,
    data: Option<serde_json::Value>,
    error: Option<String>,
    stderr_summary: Option<String>,
}

fn run_policy_scout_json(args: &[&str]) -> CliJsonResponse {
    let output = Command::new("policy-scout")
        .args(args)
        .output();

    match output {
        Ok(output) => {
            let exit_code = output.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();

            if exit_code == 0 {
                match serde_json::from_str::<serde_json::Value>(&stdout) {
                    Ok(data) => CliJsonResponse {
                        ok: true,
                        exit_code,
                        data: Some(data),
                        error: None,
                        stderr_summary: None,
                    },
                    Err(_) => CliJsonResponse {
                        ok: false,
                        exit_code,
                        data: None,
                        error: Some("Failed to parse JSON output".to_string()),
                        stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                    },
                }
            } else {
                CliJsonResponse {
                    ok: false,
                    exit_code,
                    data: None,
                    error: Some(format!("Command failed with exit code {}", exit_code)),
                    stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                }
            }
        }
        Err(e) => CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!("Failed to execute command: {}", e)),
            stderr_summary: None,
        },
    }
}

// Check-specific helper that accepts exit codes 0, 10, 20 as valid decision statuses
// For policy-scout check --json:
// - exit 0 = ALLOW
// - exit 10 = SANDBOX_FIRST
// - exit 20 = DENY
// - exit 30 = DENY_AND_ALERT
// These are decision statuses, not errors. The JSON payload contains the decision.
fn run_policy_scout_check_json(command_text: &str) -> CliJsonResponse {
    let output = Command::new("policy-scout")
        .args(["check", "--json", command_text])
        .output();

    match output {
        Ok(output) => {
            let exit_code = output.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();

            // Accept exit codes 0, 10, 20, 30 as valid check decision statuses
            let is_valid_check_exit = exit_code == 0 || exit_code == 10 || exit_code == 20 || exit_code == 30;

            if is_valid_check_exit {
                match serde_json::from_str::<serde_json::Value>(&stdout) {
                    Ok(data) => CliJsonResponse {
                        ok: true,
                        exit_code,
                        data: Some(data),
                        error: None,
                        stderr_summary: None,
                    },
                    Err(_) => CliJsonResponse {
                        ok: false,
                        exit_code,
                        data: None,
                        error: Some("Failed to parse JSON output".to_string()),
                        stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                    },
                }
            } else {
                CliJsonResponse {
                    ok: false,
                    exit_code,
                    data: None,
                    error: Some(format!("Command failed with exit code {}", exit_code)),
                    stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                }
            }
        }
        Err(e) => CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!("Failed to execute command: {}", e)),
            stderr_summary: None,
        },
    }
}

#[tauri::command]
fn get_doctor_status() -> CliJsonResponse {
    run_policy_scout_json(&["doctor", "--json"])
}

#[tauri::command]
fn get_data_status() -> CliJsonResponse {
    run_policy_scout_json(&["data", "status", "--json"])
}

#[tauri::command]
fn get_audit_stats() -> CliJsonResponse {
    run_policy_scout_json(&["audit", "stats", "--json"])
}

fn validate_cleanup_target(target: &str) -> Result<(), CliJsonResponse> {
    const ALLOWED: &[&str] = &["demo", "sandbox", "sandbox-results"];
    if ALLOWED.contains(&target) {
        Ok(())
    } else {
        Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!(
                "Invalid cleanup target: '{}'. Must be one of: demo, sandbox, sandbox-results.",
                target
            )),
            stderr_summary: None,
        })
    }
}

fn validate_command_text(command_text: &str) -> Result<(), CliJsonResponse> {
    const MAX_COMMAND_TEXT_CHARS: usize = 4000;

    // Reject empty string
    if command_text.is_empty() {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text cannot be empty".to_string()),
            stderr_summary: None,
        });
    }

    // Reject whitespace-only string
    if command_text.trim().is_empty() {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text cannot be whitespace-only".to_string()),
            stderr_summary: None,
        });
    }

    // Reject strings containing NUL characters
    if command_text.contains('\0') {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Command text cannot contain NUL characters".to_string()),
            stderr_summary: None,
        });
    }

    // Reject strings over max length
    if command_text.len() > MAX_COMMAND_TEXT_CHARS {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!(
                "Command text too long (max {} characters)",
                MAX_COMMAND_TEXT_CHARS
            )),
            stderr_summary: None,
        });
    }

    Ok(())
}

#[tauri::command]
fn get_cleanup_dry_run(target: String) -> CliJsonResponse {
    if let Err(e) = validate_cleanup_target(target.as_str()) {
        return e;
    }
    run_policy_scout_json(&["data", "cleanup", "--target", target.as_str(), "--dry-run", "--json"])
}

#[tauri::command]
fn run_eval() -> CliJsonResponse {
    run_policy_scout_json(&["eval", "run", "--json"])
}

#[tauri::command]
fn run_sweep_quick() -> CliJsonResponse {
    run_policy_scout_json(&["sweep", "quick", "--json"])
}

#[tauri::command]
fn run_sweep_project() -> CliJsonResponse {
    run_policy_scout_json(&["sweep", "project", "--json"])
}

#[tauri::command]
fn check_command(command_text: String) -> CliJsonResponse {
    if let Err(e) = validate_command_text(&command_text) {
        return e;
    }
    run_policy_scout_check_json(&command_text)
}

#[tauri::command]
fn list_sandbox_results(limit: u32, offset: Option<u32>) -> CliJsonResponse {
    let validated_limit = match validate_limit(limit) {
        Ok(l) => l,
        Err(e) => return e,
    };
    let validated_offset = match validate_pagination(offset.unwrap_or(0)) {
        Ok(o) => o,
        Err(e) => return e,
    };
    let limit_str = validated_limit.to_string();
    let offset_str = validated_offset.to_string();
    // report list --json now returns { reports: [...], total_count: N, offset: N } directly
    run_policy_scout_json(&["report", "list", "--json", "--type", "sandbox_result", "--limit", &limit_str, "--offset", &offset_str])
}

fn validate_limit(limit: u32) -> Result<u32, CliJsonResponse> {
    const ALLOWED: &[u32] = &[5, 10, 25, 50];
    if ALLOWED.contains(&limit) {
        Ok(limit)
    } else {
        Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!("Invalid limit: {}. Must be one of: 5, 10, 25, 50.", limit)),
            stderr_summary: None,
        })
    }
}

fn validate_pagination(offset: u32) -> Result<u32, CliJsonResponse> {
    if offset > 10_000 {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!("Invalid offset: {}. Must be <= 10000.", offset)),
            stderr_summary: None,
        });
    }
    Ok(offset)
}

fn validate_report_type(report_type: &str) -> Result<(), CliJsonResponse> {
    const ALLOWED: &[&str] = &[
        "command_decision",
        "sandbox_result",
        "project_sweep",
        "system_quick_sweep",
    ];
    if ALLOWED.contains(&report_type) {
        Ok(())
    } else {
        Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!(
                "Invalid report_type: '{}'. Must be one of: command_decision, sandbox_result, project_sweep, system_quick_sweep.",
                report_type
            )),
            stderr_summary: None,
        })
    }
}

fn validate_report_id(report_id: &str) -> Result<(), CliJsonResponse> {
    if report_id.is_empty() {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid report_id: cannot be empty".to_string()),
            stderr_summary: None,
        });
    }
    if !report_id.starts_with("report_") {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid report_id: must start with 'report_'".to_string()),
            stderr_summary: None,
        });
    }
    let dangerous_chars = [' ', '/', '\\', '\t', '\n', '\r', ';', '&', '|', '$', '`', '(', ')', '<', '>'];
    for c in dangerous_chars.iter() {
        if report_id.contains(*c) {
            return Err(CliJsonResponse {
                ok: false,
                exit_code: -1,
                data: None,
                error: Some(format!("Invalid report_id: contains dangerous character '{}'", c)),
                stderr_summary: None,
            });
        }
    }
    Ok(())
}

#[tauri::command]
fn show_report(report_id: String) -> CliJsonResponse {
    if let Err(e) = validate_report_id(&report_id) {
        return e;
    }
    run_policy_scout_json(&["report", "show", &report_id, "--json"])
}

#[tauri::command]
fn show_sandbox_result(report_id: String) -> CliJsonResponse {
    if let Err(e) = validate_report_id(&report_id) {
        return e;
    }
    run_policy_scout_json(&["report", "show", &report_id, "--json"])
}

#[tauri::command]
fn list_reports_filtered(limit: u32, report_type: Option<String>, offset: Option<u32>) -> CliJsonResponse {
    let validated_limit = match validate_limit(limit) {
        Ok(l) => l,
        Err(e) => return e,
    };
    let validated_offset = match validate_pagination(offset.unwrap_or(0)) {
        Ok(o) => o,
        Err(e) => return e,
    };
    let limit_str = validated_limit.to_string();
    let offset_str = validated_offset.to_string();
    if let Some(ref rt) = report_type {
        if !rt.is_empty() {
            if let Err(e) = validate_report_type(rt.as_str()) {
                return e;
            }
            return run_policy_scout_json(&[
                "report", "list", "--json", "--limit", &limit_str, "--offset", &offset_str, "--type", rt.as_str(),
            ]);
        }
    }
    run_policy_scout_json(&["report", "list", "--json", "--limit", &limit_str, "--offset", &offset_str])
}

fn validate_audit_event_type(event_type: &str) -> Result<(), CliJsonResponse> {
    const ALLOWED: &[&str] = &[
        "SweepCompleted",
        "SweepError",
        "SandboxInstallCompleted",
        "SandboxInstallStarted",
        "SandboxResultWritten",
        "ScoutReportGenerated",
        "CommandExecutionCompleted",
        "CommandExecutionBlocked",
        "ApprovalRequested",
        "ApprovalApprovedOnce",
        "ApprovalDeniedOnce",
        "DecisionIssued",
    ];
    if ALLOWED.contains(&event_type) {
        Ok(())
    } else {
        Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some(format!(
                "Invalid event_type: '{}'. Must be one of the allowlisted audit event types.",
                event_type
            )),
            stderr_summary: None,
        })
    }
}

#[tauri::command]
fn list_audit_events_filtered(event_type: Option<String>, limit: u32, offset: Option<u32>) -> CliJsonResponse {
    let validated_limit = match validate_limit(limit) {
        Ok(l) => l,
        Err(e) => return e,
    };
    let validated_offset = match validate_pagination(offset.unwrap_or(0)) {
        Ok(o) => o,
        Err(e) => return e,
    };
    let limit_str = validated_limit.to_string();
    let offset_str = validated_offset.to_string();
    if let Some(ref et) = event_type {
        if !et.is_empty() && et != "all" {
            if let Err(e) = validate_audit_event_type(et.as_str()) {
                return e;
            }
            // audit type --json now returns { events: [...], total_count: N } directly
            return run_policy_scout_json(&["audit", "type", "--json", "--limit", &limit_str, "--offset", &offset_str, et.as_str()]);
        }
    }
    run_policy_scout_json(&["audit", "list", "--json", "--limit", &limit_str, "--offset", &offset_str])
}

fn validate_audit_event_id(event_id: &str) -> Result<(), CliJsonResponse> {
    if event_id.is_empty() {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid event_id: cannot be empty".to_string()),
            stderr_summary: None,
        });
    }
    if !event_id.starts_with("evt_") {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid event_id: must start with 'evt_'".to_string()),
            stderr_summary: None,
        });
    }
    let dangerous_chars = [' ', '/', '\\', '\t', '\n', '\r', ';', '&', '|', '$', '`', '(', ')', '<', '>'];
    for c in dangerous_chars.iter() {
        if event_id.contains(*c) {
            return Err(CliJsonResponse {
                ok: false,
                exit_code: -1,
                data: None,
                error: Some(format!("Invalid event_id: contains dangerous character '{}'", c)),
                stderr_summary: None,
            });
        }
    }
    Ok(())
}

#[tauri::command]
fn show_audit_event(event_id: String) -> CliJsonResponse {
    if let Err(e) = validate_audit_event_id(&event_id) {
        return e;
    }
    run_policy_scout_json(&["audit", "show", &event_id, "--json"])
}

#[tauri::command]
fn get_policy_overview() -> CliJsonResponse {
    run_policy_scout_json(&["policy", "show", "--json"])
}

#[tauri::command]
fn run_policy_validate() -> CliJsonResponse {
    run_policy_scout_json(&["policy", "validate", "--json"])
}

fn validate_approval_id(approval_id: &str) -> Result<(), CliJsonResponse> {
    if approval_id.is_empty() {
        return Err(CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some("Invalid approval_id: cannot be empty".to_string()),
            stderr_summary: None,
        });
    }
    if !approval_id.starts_with("appr_") {
        return Err(CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some("Invalid approval_id: must start with 'appr_'".to_string()),
            stderr_summary: None,
        });
    }
    let dangerous_chars = [' ', '/', '\\', '\t', '\n', '\r', ';', '&', '|', '$', '`', '(', ')', '<', '>'];
    for c in dangerous_chars.iter() {
        if approval_id.contains(*c) {
            return Err(CliJsonResponse {
                ok: false, exit_code: -1, data: None,
                error: Some(format!("Invalid approval_id: contains dangerous character '{}'", c)),
                stderr_summary: None,
            });
        }
    }
    Ok(())
}

fn validate_sandbox_id(sandbox_id: &str) -> Result<(), CliJsonResponse> {
    if sandbox_id.is_empty() {
        return Err(CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some("Invalid sandbox_id: cannot be empty".to_string()),
            stderr_summary: None,
        });
    }
    if !sandbox_id.starts_with("sbx_") {
        return Err(CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some("Invalid sandbox_id: must start with 'sbx_'".to_string()),
            stderr_summary: None,
        });
    }
    let dangerous_chars = [' ', '/', '\\', '\t', '\n', '\r', ';', '&', '|', '$', '`', '(', ')', '<', '>'];
    for c in dangerous_chars.iter() {
        if sandbox_id.contains(*c) {
            return Err(CliJsonResponse {
                ok: false, exit_code: -1, data: None,
                error: Some(format!("Invalid sandbox_id: contains dangerous character '{}'", c)),
                stderr_summary: None,
            });
        }
    }
    Ok(())
}

fn run_sandbox_migrate_json(sandbox_id: &str, dry_run: bool) -> CliJsonResponse {
    let mut args = vec!["sandbox", "--json"];
    if dry_run {
        args.push("--dry-run");
    } else {
        args.push("--yes");
    }
    args.push(sandbox_id);

    let output = Command::new("policy-scout").args(&args).output();
    match output {
        Ok(output) => {
            let exit_code = output.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            // 0 = success/dry-run plan; 1 = blocked or failed but JSON still produced
            if exit_code == 0 || exit_code == 1 {
                match serde_json::from_str::<serde_json::Value>(&stdout) {
                    Ok(data) => CliJsonResponse {
                        ok: exit_code == 0, exit_code, data: Some(data), error: None, stderr_summary: None,
                    },
                    Err(_) => CliJsonResponse {
                        ok: false, exit_code, data: None,
                        error: Some("Failed to parse migration JSON output".to_string()),
                        stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                    },
                }
            } else {
                CliJsonResponse {
                    ok: false, exit_code, data: None,
                    error: Some(stderr.lines().take(3).collect::<Vec<_>>().join(" — ").trim().to_string()),
                    stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                }
            }
        }
        Err(e) => CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some(format!("Failed to execute migration command: {}", e)),
            stderr_summary: None,
        },
    }
}

#[tauri::command]
fn run_sandbox_migrate_dry_run(sandbox_id: String) -> CliJsonResponse {
    if let Err(e) = validate_sandbox_id(&sandbox_id) {
        return e;
    }
    run_sandbox_migrate_json(&sandbox_id, true)
}

#[tauri::command]
fn run_sandbox_migrate(sandbox_id: String) -> CliJsonResponse {
    if let Err(e) = validate_sandbox_id(&sandbox_id) {
        return e;
    }
    run_sandbox_migrate_json(&sandbox_id, false)
}

#[tauri::command]
fn get_lockdown_status() -> CliJsonResponse {
    run_policy_scout_json(&["lockdown", "status", "--json"])
}

#[tauri::command]
fn get_watch_status() -> CliJsonResponse {
    run_policy_scout_json(&["watch", "status", "--json"])
}

#[tauri::command]
fn list_approvals() -> CliJsonResponse {
    run_policy_scout_json(&["approvals", "list", "--json"])
}

#[tauri::command]
fn approve_request(approval_id: String) -> CliJsonResponse {
    if let Err(e) = validate_approval_id(&approval_id) {
        return e;
    }
    run_policy_scout_json(&["approvals", "approve", &approval_id, "--json"])
}

#[tauri::command]
fn deny_request(approval_id: String) -> CliJsonResponse {
    if let Err(e) = validate_approval_id(&approval_id) {
        return e;
    }
    run_policy_scout_json(&["approvals", "deny", &approval_id, "--json"])
}

fn run_sandbox_install_json(command_text: &str) -> CliJsonResponse {
    let parts: Vec<&str> = command_text.split_whitespace().collect();
    let mut args = vec!["sandbox", "--json", "--"];
    args.extend_from_slice(&parts);

    let output = Command::new("policy-scout").args(&args).output();
    match output {
        Ok(output) => {
            let exit_code = output.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            // 0 = install succeeded, 20 = install failed but result JSON still produced
            let is_valid_exit = exit_code == 0 || exit_code == 20;
            if is_valid_exit {
                match serde_json::from_str::<serde_json::Value>(&stdout) {
                    Ok(data) => CliJsonResponse { ok: true, exit_code, data: Some(data), error: None, stderr_summary: None },
                    Err(_) => CliJsonResponse {
                        ok: false, exit_code, data: None,
                        error: Some("Failed to parse sandbox JSON output".to_string()),
                        stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                    },
                }
            } else {
                CliJsonResponse {
                    ok: false, exit_code, data: None,
                    error: Some(stderr.lines().take(3).collect::<Vec<_>>().join(" — ").trim().to_string()),
                    stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                }
            }
        }
        Err(e) => CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some(format!("Failed to execute sandbox command: {}", e)),
            stderr_summary: None,
        },
    }
}

#[tauri::command]
fn run_sandbox_install(command_text: String) -> CliJsonResponse {
    if let Err(e) = validate_command_text(&command_text) {
        return e;
    }
    run_sandbox_install_json(&command_text)
}

#[tauri::command]
fn open_terminal() -> Result<(), String> {
    // Honour the user's preferred terminal if set
    if let Ok(term) = std::env::var("TERMINAL") {
        if !term.is_empty() {
            if Command::new("bash").args(["-c", &term]).spawn().is_ok() {
                return Ok(());
            }
        }
    }

    // Ordered list: try each through bash so the full user PATH is available
    let candidates: &[&str] = &[
        "x-terminal-emulator",
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "tilix",
        "mate-terminal",
        "lxterminal",
        "alacritty",
        "kitty",
        "wezterm start",
        "xterm",
        "uxterm",
    ];
    for cmd in candidates {
        if Command::new("bash").args(["-c", cmd]).spawn().is_ok() {
            return Ok(());
        }
    }
    Err("No terminal emulator found. Install xterm or set the TERMINAL environment variable.".to_string())
}

#[tauri::command]
fn run_cleanup_apply(target: String) -> CliJsonResponse {
    if let Err(e) = validate_cleanup_target(target.as_str()) {
        return e;
    }
    run_policy_scout_json(&["data", "cleanup", "--target", target.as_str(), "--apply", "--yes", "--json"])
}

fn validate_path(path: &str) -> Result<(), CliJsonResponse> {
    if path.contains('\0') {
        return Err(CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some("Path cannot contain NUL characters".to_string()),
            stderr_summary: None,
        });
    }
    if path.len() > 4096 {
        return Err(CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some("Path too long (max 4096 characters)".to_string()),
            stderr_summary: None,
        });
    }
    Ok(())
}

#[tauri::command]
fn run_scan_dir(path: Option<String>) -> CliJsonResponse {
    if let Some(ref p) = path {
        if !p.is_empty() {
            if let Err(e) = validate_path(p) { return e; }
            return run_policy_scout_json(&["scan", "dir", "--json", p.as_str()]);
        }
    }
    run_policy_scout_json(&["scan", "dir", "--json"])
}

#[tauri::command]
fn run_scan_staged(repo: Option<String>) -> CliJsonResponse {
    if let Some(ref r) = repo {
        if !r.is_empty() {
            if let Err(e) = validate_path(r) { return e; }
            return run_policy_scout_json(&["scan", "staged", "--json", "--repo", r.as_str()]);
        }
    }
    run_policy_scout_json(&["scan", "staged", "--json"])
}

#[tauri::command]
fn run_scan_history(repo: Option<String>, max_commits: Option<u32>) -> CliJsonResponse {
    let max_str = max_commits.map(|n| n.min(1000).to_string());
    let mut args: Vec<&str> = vec!["scan", "history", "--json"];
    if let Some(ref s) = max_str {
        args.push("--max-commits");
        args.push(s.as_str());
    }
    if let Some(ref r) = repo {
        if !r.is_empty() {
            if let Err(e) = validate_path(r) { return e; }
            args.push("--repo");
            args.push(r.as_str());
        }
    }
    run_policy_scout_json(&args)
}

#[tauri::command]
fn run_scan_injection(path: Option<String>) -> CliJsonResponse {
    if let Some(ref p) = path {
        if !p.is_empty() {
            if let Err(e) = validate_path(p) { return e; }
            return run_policy_scout_json(&["scan", "injection", "--json", p.as_str()]);
        }
    }
    run_policy_scout_json(&["scan", "injection", "--json"])
}

#[tauri::command]
fn run_policy_simulate(command_text: String) -> CliJsonResponse {
    if let Err(e) = validate_command_text(&command_text) {
        return e;
    }
    run_policy_scout_json(&["policy", "simulate", "--json", command_text.as_str()])
}

// verify-chain: exit 0 = verified, exit 1 = errors found — both return valid JSON
fn run_policy_scout_verify_chain_json() -> CliJsonResponse {
    let output = Command::new("policy-scout")
        .args(["audit", "verify-chain", "--json"])
        .output();
    match output {
        Ok(output) => {
            let exit_code = output.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            if exit_code == 0 || exit_code == 1 {
                match serde_json::from_str::<serde_json::Value>(&stdout) {
                    Ok(data) => CliJsonResponse {
                        ok: exit_code == 0,
                        exit_code,
                        data: Some(data),
                        error: if exit_code == 1 { Some("Integrity errors found".to_string()) } else { None },
                        stderr_summary: None,
                    },
                    Err(_) => CliJsonResponse {
                        ok: false, exit_code, data: None,
                        error: Some("Failed to parse verify-chain JSON output".to_string()),
                        stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                    },
                }
            } else {
                CliJsonResponse {
                    ok: false, exit_code, data: None,
                    error: Some(format!("verify-chain failed with exit code {}", exit_code)),
                    stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                }
            }
        }
        Err(e) => CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some(format!("Failed to execute command: {}", e)),
            stderr_summary: None,
        },
    }
}

// run gate: exit 0 = command executed, exit 10/20/30 = blocked — all return valid JSON
// ok=true only when the command was actually executed (exit 0)
fn run_policy_scout_run_gate_json(command_text: &str) -> CliJsonResponse {
    let output = Command::new("policy-scout")
        .args(["run", "--json", command_text])
        .output();
    match output {
        Ok(output) => {
            let exit_code = output.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            let is_valid_exit = exit_code == 0 || exit_code == 10 || exit_code == 20 || exit_code == 30;
            if is_valid_exit {
                match serde_json::from_str::<serde_json::Value>(&stdout) {
                    Ok(data) => CliJsonResponse {
                        ok: exit_code == 0,
                        exit_code,
                        data: Some(data),
                        error: if exit_code != 0 {
                            Some(format!("Command blocked by policy (exit {})", exit_code))
                        } else {
                            None
                        },
                        stderr_summary: None,
                    },
                    Err(_) => CliJsonResponse {
                        ok: false, exit_code, data: None,
                        error: Some("Failed to parse run JSON output".to_string()),
                        stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                    },
                }
            } else {
                CliJsonResponse {
                    ok: false, exit_code, data: None,
                    error: Some(stderr.lines().take(3).collect::<Vec<_>>().join(" — ").trim().to_string()),
                    stderr_summary: Some(stderr.lines().take(3).collect::<Vec<_>>().join("\n")),
                }
            }
        }
        Err(e) => CliJsonResponse {
            ok: false, exit_code: -1, data: None,
            error: Some(format!("Failed to execute run command: {}", e)),
            stderr_summary: None,
        },
    }
}

#[tauri::command]
fn run_audit_verify_chain() -> CliJsonResponse {
    run_policy_scout_verify_chain_json()
}

#[tauri::command]
fn run_command_through_gate(command_text: String) -> CliJsonResponse {
    if let Err(e) = validate_command_text(&command_text) {
        return e;
    }
    run_policy_scout_run_gate_json(&command_text)
}

fn validate_reason(reason: &str) -> Result<(), CliJsonResponse> {
    if reason.len() > 500 {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Reason too long (max 500 characters)".to_string()),
            stderr_summary: None,
        });
    }
    if reason.contains('\0') {
        return Err(CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Reason cannot contain NUL characters".to_string()),
            stderr_summary: None,
        });
    }
    Ok(())
}

#[tauri::command]
fn activate_lockdown(reason: Option<String>) -> CliJsonResponse {
    let reason_str = reason.unwrap_or_default();
    if let Err(e) = validate_reason(&reason_str) {
        return e;
    }
    if reason_str.is_empty() {
        run_policy_scout_json(&["lockdown", "on", "--json"])
    } else {
        run_policy_scout_json(&["lockdown", "on", "--reason", &reason_str, "--json"])
    }
}

#[tauri::command]
fn deactivate_lockdown() -> CliJsonResponse {
    run_policy_scout_json(&["lockdown", "off", "--json"])
}

#[tauri::command]
fn restart_watch() -> CliJsonResponse {
    // best-effort stop — ignore output; daemon may not be running
    let _ = Command::new("policy-scout").args(["watch", "stop"]).output();
    run_policy_scout_json(&["watch", "start", "--json"])
}

// Returns combined lockdown + watch status in one call for Lattica integration
#[tauri::command]
fn get_system_health() -> CliJsonResponse {
    let lockdown = run_policy_scout_json(&["lockdown", "status", "--json"]);
    let watch = run_policy_scout_json(&["watch", "status", "--json"]);
    let combined = serde_json::json!({
        "lockdown": lockdown.data,
        "watch": watch.data,
    });
    let ok = lockdown.ok && watch.ok;
    let error = match (lockdown.error, watch.error) {
        (Some(l), Some(w)) => Some(format!("lockdown: {}; watch: {}", l, w)),
        (Some(l), None)    => Some(format!("lockdown: {}", l)),
        (None,    Some(w)) => Some(format!("watch: {}", w)),
        (None,    None)    => None,
    };
    CliJsonResponse {
        ok,
        exit_code: if ok { 0 } else { -1 },
        data: Some(combined),
        error,
        stderr_summary: None,
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_doctor_status,
            get_data_status,
            get_audit_stats,
            get_cleanup_dry_run,
            run_eval,
            run_sweep_quick,
            run_sweep_project,
            check_command,
            list_sandbox_results,
            list_reports_filtered,
            show_report,
            show_sandbox_result,
            list_audit_events_filtered,
            show_audit_event,
            get_policy_overview,
            run_policy_validate,
            run_policy_simulate,
            run_cleanup_apply,
            run_sandbox_migrate_dry_run,
            run_sandbox_migrate,
            get_lockdown_status,
            get_watch_status,
            activate_lockdown,
            deactivate_lockdown,
            restart_watch,
            list_approvals,
            approve_request,
            deny_request,
            run_sandbox_install,
            open_terminal,
            run_scan_dir,
            run_scan_staged,
            run_scan_history,
            run_scan_injection,
            run_audit_verify_chain,
            run_command_through_gate,
            get_system_health
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    // validate_limit

    #[test]
    fn test_validate_limit_accepts_allowed_values() {
        assert!(validate_limit(5).is_ok());
        assert!(validate_limit(10).is_ok());
        assert!(validate_limit(25).is_ok());
        assert!(validate_limit(50).is_ok());
    }

    #[test]
    fn test_validate_limit_rejects_unknown_values() {
        assert!(validate_limit(0).is_err());
        assert!(validate_limit(1).is_err());
        assert!(validate_limit(20).is_err());
        assert!(validate_limit(100).is_err());
        assert!(validate_limit(u32::MAX).is_err());
    }

    // validate_report_type

    #[test]
    fn test_validate_report_type_accepts_allowed_values() {
        assert!(validate_report_type("command_decision").is_ok());
        assert!(validate_report_type("sandbox_result").is_ok());
        assert!(validate_report_type("project_sweep").is_ok());
        assert!(validate_report_type("system_quick_sweep").is_ok());
    }

    #[test]
    fn test_validate_report_type_rejects_unknown_values() {
        assert!(validate_report_type("").is_err());
        assert!(validate_report_type("sandbox").is_err());
        assert!(validate_report_type("unknown_type").is_err());
        assert!(validate_report_type("sandbox_result;rm -rf /").is_err());
        assert!(validate_report_type("CommandDecision").is_err());
    }

    // validate_report_id

    #[test]
    fn test_validate_report_id_accepts_valid_ids() {
        assert!(validate_report_id("report_abc123").is_ok());
        assert!(validate_report_id("report_20260607_demo").is_ok());
    }

    #[test]
    fn test_validate_report_id_rejects_invalid_ids() {
        assert!(validate_report_id("").is_err());
        assert!(validate_report_id("abc123").is_err());
        assert!(validate_report_id("evt_abc123").is_err());
        assert!(validate_report_id("report_bad;rm").is_err());
        assert!(validate_report_id("report_bad/../x").is_err());
        assert!(validate_report_id("report_bad|x").is_err());
    }

    // validate_audit_event_type

    #[test]
    fn test_validate_audit_event_type_accepts_allowed_values() {
        assert!(validate_audit_event_type("SweepCompleted").is_ok());
        assert!(validate_audit_event_type("SweepError").is_ok());
        assert!(validate_audit_event_type("SandboxInstallCompleted").is_ok());
        assert!(validate_audit_event_type("SandboxInstallStarted").is_ok());
        assert!(validate_audit_event_type("SandboxResultWritten").is_ok());
        assert!(validate_audit_event_type("ScoutReportGenerated").is_ok());
        assert!(validate_audit_event_type("CommandExecutionCompleted").is_ok());
        assert!(validate_audit_event_type("CommandExecutionBlocked").is_ok());
        assert!(validate_audit_event_type("ApprovalRequested").is_ok());
        assert!(validate_audit_event_type("ApprovalApprovedOnce").is_ok());
        assert!(validate_audit_event_type("ApprovalDeniedOnce").is_ok());
        assert!(validate_audit_event_type("DecisionIssued").is_ok());
    }

    #[test]
    fn test_validate_audit_event_type_rejects_unknown_values() {
        assert!(validate_audit_event_type("").is_err());
        assert!(validate_audit_event_type("UnknownEvent").is_err());
        assert!(validate_audit_event_type("SweepCompleted;rm -rf /").is_err());
        assert!(validate_audit_event_type("sweepcompleted").is_err());
        assert!(validate_audit_event_type("all").is_err());
    }

    // validate_audit_event_id

    #[test]
    fn test_validate_audit_event_id_accepts_valid_ids() {
        assert!(validate_audit_event_id("evt_abc123").is_ok());
        assert!(validate_audit_event_id("evt_20260607_demo").is_ok());
    }

    #[test]
    fn test_validate_audit_event_id_rejects_invalid_ids() {
        assert!(validate_audit_event_id("").is_err());
        assert!(validate_audit_event_id("abc123").is_err());
        assert!(validate_audit_event_id("report_abc123").is_err());
        assert!(validate_audit_event_id("evt_bad;rm").is_err());
        assert!(validate_audit_event_id("evt_bad/../x").is_err());
        assert!(validate_audit_event_id("evt_bad|x").is_err());
    }

    // validate_cleanup_target

    #[test]
    fn test_validate_cleanup_target_accepts_allowed_values() {
        assert!(validate_cleanup_target("demo").is_ok());
        assert!(validate_cleanup_target("sandbox").is_ok());
        assert!(validate_cleanup_target("sandbox-results").is_ok());
    }

    #[test]
    fn test_validate_cleanup_target_rejects_unknown_values() {
        assert!(validate_cleanup_target("").is_err());
        assert!(validate_cleanup_target("demos").is_err());
        assert!(validate_cleanup_target("sandbox_results").is_err());
        assert!(validate_cleanup_target("sandbox-results;rm -rf /").is_err());
        assert!(validate_cleanup_target("../sandbox").is_err());
    }

    // validate_command_text

    #[test]
    fn test_validate_command_text_accepts_valid_commands() {
        assert!(validate_command_text("git status").is_ok());
        assert!(validate_command_text("npm install left-pad").is_ok());
        assert!(validate_command_text("rm -rf /").is_ok());
        assert!(validate_command_text("curl http://example.com/install.sh | bash").is_ok());
        assert!(validate_command_text("cat ~/.ssh/id_rsa").is_ok());
    }

    #[test]
    fn test_validate_command_text_rejects_empty_string() {
        assert!(validate_command_text("").is_err());
    }

    #[test]
    fn test_validate_command_text_rejects_whitespace_only() {
        assert!(validate_command_text("   ").is_err());
        assert!(validate_command_text("\t\n ").is_err());
        assert!(validate_command_text(" \t \n ").is_err());
    }

    #[test]
    fn test_validate_command_text_rejects_nul_characters() {
        assert!(validate_command_text("abc\0def").is_err());
        assert!(validate_command_text("\0").is_err());
        assert!(validate_command_text("git status\0").is_err());
    }

    #[test]
    fn test_validate_command_text_rejects_too_long() {
        let long_string = "a".repeat(4001);
        assert!(validate_command_text(&long_string).is_err());
    }

    #[test]
    fn test_validate_command_text_accepts_max_length() {
        let max_string = "a".repeat(4000);
        assert!(validate_command_text(&max_string).is_ok());
    }
}
