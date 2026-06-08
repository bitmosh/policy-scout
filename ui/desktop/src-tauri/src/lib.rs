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
fn list_sandbox_results() -> CliJsonResponse {
    run_policy_scout_json(&["report", "list", "--json", "--type", "sandbox_result", "--limit", "5"])
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
fn list_reports_filtered(limit: u32, report_type: Option<String>) -> CliJsonResponse {
    let validated_limit = match validate_limit(limit) {
        Ok(l) => l,
        Err(e) => return e,
    };
    let limit_str = validated_limit.to_string();
    if let Some(ref rt) = report_type {
        if !rt.is_empty() {
            if let Err(e) = validate_report_type(rt.as_str()) {
                return e;
            }
            return run_policy_scout_json(&[
                "report", "list", "--json", "--limit", &limit_str, "--type", rt.as_str(),
            ]);
        }
    }
    run_policy_scout_json(&["report", "list", "--json", "--limit", &limit_str])
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
fn list_audit_events_filtered(event_type: Option<String>) -> CliJsonResponse {
    if let Some(ref et) = event_type {
        if !et.is_empty() && et != "all" {
            if let Err(e) = validate_audit_event_type(et.as_str()) {
                return e;
            }
            return run_policy_scout_json(&["audit", "type", "--json", et.as_str()]);
        }
    }
    run_policy_scout_json(&["audit", "list", "--json", "--limit", "10"])
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
            list_sandbox_results,
            list_reports_filtered,
            show_report,
            show_sandbox_result,
            list_audit_events_filtered,
            show_audit_event
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
