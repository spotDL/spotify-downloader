/** `248000` → `"4:08"`. Null/negative durations render as `"—"`. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null || ms < 0) return "\u2014";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Join an artist list into a display string. */
export function joinArtists(artists: readonly string[]): string {
  return artists.join(", ");
}

/**
 * Compact a follower/listener count with a K/M/B suffix, e.g.
 * `33901227` → `"33.9M"`, `1234` → `"1.2K"`, `842` → `"842"`. One decimal
 * below 100 of a unit (dropped when `.0`); null/negative render as `"—"`.
 */
export function formatFollowers(n: number | null | undefined): string {
  if (n == null || n < 0) return "—";
  const units = [
    { value: 1e9, suffix: "B" },
    { value: 1e6, suffix: "M" },
    { value: 1e3, suffix: "K" },
  ];
  for (const { value, suffix } of units) {
    if (n >= value) {
      const scaled = n / value;
      const rounded =
        scaled >= 100 ? Math.round(scaled) : Math.round(scaled * 10) / 10;
      return `${rounded}${suffix}`;
    }
  }
  return String(n);
}

/** Join truthy parts with a middle dot, e.g. `"2013 · 12 tracks"`. */
export function joinMeta(parts: Array<string | number | null | undefined>): string {
  return parts.filter((p) => p != null && p !== "").join(" · ");
}
