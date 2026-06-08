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
fn list_reports() -> CliJsonResponse {
    run_policy_scout_json(&["report", "list", "--json", "--limit", "5"])
}

#[tauri::command]
fn get_audit_stats() -> CliJsonResponse {
    run_policy_scout_json(&["audit", "stats", "--json"])
}

#[tauri::command]
fn get_cleanup_dry_run_demo() -> CliJsonResponse {
    run_policy_scout_json(&["data", "cleanup", "--target", "demo", "--dry-run", "--json"])
}

#[tauri::command]
fn get_cleanup_dry_run_sandbox() -> CliJsonResponse {
    run_policy_scout_json(&["data", "cleanup", "--target", "sandbox", "--dry-run", "--json"])
}

#[tauri::command]
fn get_cleanup_dry_run_sandbox_results() -> CliJsonResponse {
    run_policy_scout_json(&["data", "cleanup", "--target", "sandbox-results", "--dry-run", "--json"])
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
fn show_report(report_id: String) -> CliJsonResponse {
    // Validation: report_id must start with "report_"
    if !report_id.starts_with("report_") {
        return CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid report_id: must start with 'report_'".to_string()),
            stderr_summary: None,
        };
    }

    // Validation: reject empty string
    if report_id.is_empty() {
        return CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid report_id: cannot be empty".to_string()),
            stderr_summary: None,
        };
    }

    // Validation: reject spaces, path separators, shell metacharacters
    let dangerous_chars = [' ', '/', '\\', '\t', '\n', '\r', ';', '&', '|', '$', '`', '(', ')', '<', '>'];
    for c in dangerous_chars.iter() {
        if report_id.contains(*c) {
            return CliJsonResponse {
                ok: false,
                exit_code: -1,
                data: None,
                error: Some(format!("Invalid report_id: contains dangerous character '{}'", c)),
                stderr_summary: None,
            };
        }
    }

    run_policy_scout_json(&["report", "show", &report_id, "--json"])
}

#[tauri::command]
fn list_audit_events() -> CliJsonResponse {
    run_policy_scout_json(&["audit", "list", "--json", "--limit", "10"])
}

#[tauri::command]
fn show_audit_event(event_id: String) -> CliJsonResponse {
    // Validation: event_id must start with "evt_"
    if !event_id.starts_with("evt_") {
        return CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid event_id: must start with 'evt_'".to_string()),
            stderr_summary: None,
        };
    }

    // Validation: reject empty string
    if event_id.is_empty() {
        return CliJsonResponse {
            ok: false,
            exit_code: -1,
            data: None,
            error: Some("Invalid event_id: cannot be empty".to_string()),
            stderr_summary: None,
        };
    }

    // Validation: reject spaces, path separators, shell metacharacters
    let dangerous_chars = [' ', '/', '\\', '\t', '\n', '\r', ';', '&', '|', '$', '`', '(', ')', '<', '>'];
    for c in dangerous_chars.iter() {
        if event_id.contains(*c) {
            return CliJsonResponse {
                ok: false,
                exit_code: -1,
                data: None,
                error: Some(format!("Invalid event_id: contains dangerous character '{}'", c)),
                stderr_summary: None,
            };
        }
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
            list_reports,
            get_audit_stats,
            get_cleanup_dry_run_demo,
            get_cleanup_dry_run_sandbox,
            get_cleanup_dry_run_sandbox_results,
            run_eval,
            run_sweep_quick,
            run_sweep_project,
            show_report,
            list_audit_events,
            show_audit_event
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
