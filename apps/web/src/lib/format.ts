/** `248000` → `"4:08"`. Null/negative durations render as `"—"`. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null || ms < 0) return "—";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Join an artist list into a display string. */
export function joinArtists(artists: readonly string[]): string {
  return artists.join(", ");
}
