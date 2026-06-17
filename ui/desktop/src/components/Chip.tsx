import type { ReactNode } from "react";

interface ChipProps {
  tone: string;
  children: ReactNode;
  size?: number;
  dim?: boolean;
}

export function Chip({ tone, children, size = 10, dim = false }: ChipProps) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      fontFamily: "var(--font-mono)",
      fontSize: size,
      letterSpacing: "0.04em",
      color: dim ? "var(--color-text-muted)" : tone,
      background: `color-mix(in srgb, ${tone} 12%, transparent)`,
      border: `1px solid color-mix(in srgb, ${tone} 30%, transparent)`,
      borderRadius: 5,
      padding: "2px 7px",
      whiteSpace: "nowrap",
      flex: "none",
    }}>
      {children}
    </span>
  );
}
