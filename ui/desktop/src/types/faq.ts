export type GuidedFaqCategory =
  | "command_safety"
  | "package_installs"
  | "sandbox_workflow"
  | "cleanup_dry_run"
  | "sweep_findings"
  | "reports_audit"
  | "approvals"
  | "credential_hygiene"
  | "troubleshooting"
  | "dashboard_navigation";

export interface GuidedFaqPrompt {
  id: string;
  category: GuidedFaqCategory;
  label: string;
  description: string;
  exampleCommand?: string;
  explanation: string;
  safetyNote?: string;
}
