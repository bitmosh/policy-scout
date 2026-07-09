// SPDX-License-Identifier: Apache-2.0
import { IcoX } from "./Icons";

export interface ToastData {
  title: string;
  sub: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function Toast({ title, sub, actionLabel, onAction, onClose }: ToastData & { onClose: () => void }) {
  return (
    <div style={{
      position: "absolute", bottom: 18, right: 18, zIndex: 30, width: 300,
      display: "flex", gap: 12, alignItems: "flex-start",
      background: "var(--color-panel)", border: "1px solid var(--color-border-muted)",
      borderRadius: 10, padding: "13px 12px 13px 15px",
      boxShadow: "0 14px 36px rgba(0,0,0,0.55)", animation: "toastin .18s ease-out",
    }}>
      <span className="pulse" style={{ marginTop: 5 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)" }}>{title}</div>
        <div className="mono" style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 3 }}>{sub}</div>
        {actionLabel && onAction && (
          <button onClick={() => { onAction(); onClose(); }}
            style={{ marginTop: 6, background: "none", border: "none", padding: 0, cursor: "pointer", fontSize: 11.5, fontWeight: 600, color: "var(--color-info)", letterSpacing: "0.01em" }}>
            {actionLabel} →
          </button>
        )}
      </div>
      <button className="iconbtn t focusable" style={{ width: 24, height: 24 }} aria-label="Dismiss" onClick={onClose}>
        <IcoX />
      </button>
    </div>
  );
}
