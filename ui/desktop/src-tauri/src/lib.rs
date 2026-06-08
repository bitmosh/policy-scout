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
            get_cleanup_dry_run_sandbox_results
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
