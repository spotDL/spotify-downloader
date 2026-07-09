/** `248000` → `"4:08"`; `null`/negative → `""`. Used by track rows & the queue. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null || ms < 0) return "";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Join truthy parts with a middle dot, e.g. `"2013 · 12 tracks"`. */
export function joinMeta(parts: Array<string | number | null | undefined>): string {
  return parts.filter((p) => p != null && p !== "").join(" · ");
}
