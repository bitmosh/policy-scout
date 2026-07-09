// SPDX-License-Identifier: Apache-2.0
interface RedactionNoticeProps {
  show: boolean;
  message?: string;
}

export function RedactionNotice({ show, message }: RedactionNoticeProps) {
  if (!show) return null;

  return (
    <div className="redaction-notice">
      <strong>⚠️ Redaction Applied</strong>
      <p>{message || "Some data has been redacted for privacy. Redacted values are displayed as placeholders."}</p>
    </div>
  );
}
