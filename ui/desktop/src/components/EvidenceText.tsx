// SPDX-License-Identifier: Apache-2.0
interface EvidenceTextProps {
  text: string;
  className?: string;
}

const REDACTION_PATTERN = /(<redacted:[^>]+>)/g;

export function EvidenceText({ text, className = "" }: EvidenceTextProps) {
  if (!text) return null;
  const parts = text.split(REDACTION_PATTERN);
  if (parts.length === 1) {
    return <span className={className}>{text}</span>;
  }
  return (
    <span className={className}>
      {parts.map((part, i) => {
        if (part.match(/^<redacted:[^>]+>$/)) {
          return (
            <span key={i} className="redaction-placeholder" title="Protected evidence placeholder">
              {part}
            </span>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}

export function hasRedaction(text: string): boolean {
  return REDACTION_PATTERN.test(text);
}
