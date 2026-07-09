// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { CliJsonResponse, AuditVerifyChainData } from "../types";

export function AuditVerifyChainCard() {
  const [result, setResult] = useState<CliJsonResponse<AuditVerifyChainData> | null>(null);
  const [loading, setLoading] = useState(false);

  async function runVerifyChain() {
    setLoading(true);
    try {
      const r = await invoke<CliJsonResponse<AuditVerifyChainData>>("run_audit_verify_chain");
      setResult(r);
    } catch (e) {
      setResult({
        ok: false, exit_code: -1,
        data: null as unknown as AuditVerifyChainData,
        error: String(e), stderr_summary: null,
      });
    } finally {
      setLoading(false);
    }
  }

  const data = result?.data;
  const isVerified = data?.verified === true;

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
        <div>
          <div className="eyebrow">Chain Integrity</div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>
            Verify HMAC chain integrity of the audit log — detects gaps and tampered entries.
          </div>
        </div>
        <button
          onClick={runVerifyChain}
          disabled={loading}
          style={{
            padding: "6px 14px", fontSize: 12, fontWeight: 600,
            background: loading ? "var(--color-elevated)" : "var(--color-info)",
            color: loading ? "var(--color-text-muted)" : "#fff",
            border: "1px solid var(--color-border)", borderRadius: 6,
            cursor: loading ? "not-allowed" : "pointer", flexShrink: 0,
          }}
        >
          {loading ? "Verifying…" : result ? "Re-verify" : "Verify"}
        </button>
      </div>

      {result && !data && (
        <div style={{ fontSize: 12, color: "var(--color-danger)" }}>
          {result.error ?? "Verification failed."}
        </div>
      )}

      {data && (
        <>
          <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 10 }}>
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: isVerified ? "var(--color-success)" : "var(--color-danger)",
            }}>
              {isVerified ? "✓ Verified" : "✗ Integrity errors"}
            </span>
            <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
              {data.total_entries.toLocaleString()} entries checked
            </span>
          </div>

          {!isVerified && (
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 10 }}>
              {data.message}
            </div>
          )}

          {data.errors.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {data.errors.map((err, i) => (
                <div key={i} style={{
                  padding: "6px 10px",
                  background: "color-mix(in srgb, var(--color-danger) 8%, var(--color-panel))",
                  border: "1px solid color-mix(in srgb, var(--color-danger) 20%, transparent)",
                  borderRadius: 6, fontSize: 11,
                }}>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                    line {err.lineno}
                  </span>
                  {" · "}
                  <span style={{ color: "var(--color-danger)", fontWeight: 600 }}>{err.kind}</span>
                  {" · "}
                  <span style={{ color: "var(--color-text-secondary)" }}>{err.detail}</span>
                </div>
              ))}
            </div>
          )}

          {isVerified && (
            <div style={{ fontSize: 12, color: "var(--color-success)", fontWeight: 500 }}>
              All entries pass HMAC verification.
            </div>
          )}
        </>
      )}
    </div>
  );
}
