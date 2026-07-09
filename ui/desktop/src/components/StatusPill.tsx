// SPDX-License-Identifier: Apache-2.0
export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger" | "review";

interface StatusPillProps {
  label: string;
  tone: StatusTone;
  value?: string | number;
  title?: string;
  className?: string;
}

export function StatusPill({ label, tone, value, title, className }: StatusPillProps) {
  const toneClass = `status-pill status-pill--${tone}`;
  const combinedClassName = className ? `${toneClass} ${className}` : toneClass;

  return (
    <div className={combinedClassName} title={title}>
      <span className="status-pill__label">{label}:</span>
      {value !== undefined && (
        <span className="status-pill__value">{value}</span>
      )}
    </div>
  );
}

// Helper functions for tone mapping
export function severityToTone(severity: string): StatusTone {
  const s = severity?.toLowerCase();
  if (s === "critical" || s === "high") return "danger";
  if (s === "medium") return "warning";
  if (s === "low" || s === "info") return "info";
  return "neutral";
}

export function confidenceToTone(confidence: string): StatusTone {
  const c = confidence?.toLowerCase();
  if (c === "high") return "success";
  if (c === "moderate") return "warning";
  if (c === "low") return "danger";
  return "neutral";
}

export function healthStatusToTone(status: string): StatusTone {
  const s = status?.toLowerCase();
  if (s === "ok") return "success";
  if (s === "warning") return "warning";
  if (s === "error") return "danger";
  return "neutral";
}

export function evalStatusToTone(failed: number): StatusTone {
  return failed === 0 ? "success" : "danger";
}
