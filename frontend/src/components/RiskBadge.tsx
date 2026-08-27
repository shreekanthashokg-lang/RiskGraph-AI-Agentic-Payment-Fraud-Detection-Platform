export function RiskBadge({ level }: { level: string }) {
  return <span className={`badge ${level}`}>{level}</span>;
}

export function DegradedBadge({ show, reason }: { show: boolean; reason?: string | null }) {
  if (!show) return null;
  return <span className="badge degraded" title={reason ?? undefined}>DEGRADED MODE</span>;
}
