export function BrandMark() {
  return (
    <img src="/icon-transparent.png" width={28} height={28} alt="" aria-hidden="true" style={{ objectFit: "contain" }} />
  );
}

export function Motif({ size = 56, op = 0.5 }: { size?: number; op?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" style={{ opacity: op }} aria-hidden="true">
      <circle cx="11" cy="14" r="6.6" stroke="var(--color-warning)" strokeWidth="2.1" />
      <circle cx="17" cy="14" r="6.6" stroke="var(--color-info)" strokeWidth="2.1" />
    </svg>
  );
}
