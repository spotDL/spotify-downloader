// The `degraded_sources` banner (CONTRACT — spec §6): shown whenever a resolve
// or search response reports that one or more metadata sources were unavailable,
// so results may be thinner than usual. Renders nothing when no source degraded.
export function DegradedBanner({
  sources,
  className = "",
}: {
  sources: readonly string[];
  className?: string;
}) {
  if (sources.length === 0) return null;
  return (
    <div
      role="status"
      className={`rounded-card border border-warn/40 bg-warn/10 px-4 py-2.5 text-sm text-fg ${className}`}
    >
      Some sources were unavailable; results may be thinner.
      <span className="ml-1 text-muted">({sources.join(", ")})</span>
    </div>
  );
}
