import {
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { LyricsOut } from "../api/generated/types.gen";
import { Button } from "./Button";

// --- LRC parsing -------------------------------------------------------------

export type LrcLine = { timeMs: number; text: string };

const LRC_TAG = /\[(\d{1,2}):(\d{1,2})(?:[.:](\d+))?\]/g;

/**
 * Parse LRC-timestamped lyrics into time-ordered lines. Returns `null` when the
 * text carries no usable timestamps (e.g. plain lyrics mislabelled synced, or a
 * metadata-only header), so callers can fall back to a plain render.
 */
export function parseLrc(text: string): LrcLine[] | null {
  const lines: LrcLine[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const stamps = [...raw.matchAll(LRC_TAG)];
    if (stamps.length === 0) continue;
    const body = raw.replace(LRC_TAG, "").trim();
    for (const m of stamps) {
      const minutes = Number(m[1]);
      const seconds = Number(m[2]);
      const fraction = m[3] ?? "";
      // Normalize the fractional part to milliseconds (".85" → 850, ".8" → 800).
      const ms =
        fraction === ""
          ? 0
          : Number(fraction.padEnd(3, "0").slice(0, 3));
      lines.push({ timeMs: minutes * 60_000 + seconds * 1000 + ms, text: body });
    }
  }
  if (lines.length === 0) return null;
  lines.sort((a, b) => a.timeMs - b.timeMs);
  return lines;
}

/** Index of the last line whose timestamp has passed at `currentMs`. */
export function activeLineIndex(lines: LrcLine[], currentMs: number): number {
  let active = -1;
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].timeMs <= currentMs) active = i;
    else break;
  }
  return active;
}

// --- Viewer ------------------------------------------------------------------

const TICK_MS = 250;

/**
 * Synced-lyrics viewer (CONTRACT — Task 7). Given a track's lyrics variants it
 * offers a source selector, and for a `synced` variant a virtual clock that
 * advances the active line and autoscrolls it to centre. A "follow" toggle
 * re-centres and disengages when the user scrolls manually. A `synced` variant
 * with no parseable timestamps falls back to a plain render.
 *
 * `renderVote` lets the host inject the (gated) per-variant vote control; the
 * viewer itself owns no server state.
 */
export function SyncedLyricsViewer({
  lyrics,
  renderVote,
}: {
  lyrics: LyricsOut[];
  renderVote?: (lyric: LyricsOut) => ReactNode;
}) {
  const [selectedId, setSelectedId] = useState<string>(() => {
    const synced = lyrics.find((l) => l.kind === "synced");
    return (synced ?? lyrics[0])?.id ?? "";
  });
  const selected =
    lyrics.find((l) => l.id === selectedId) ?? lyrics[0] ?? null;

  const parsed = useMemo(
    () =>
      selected && selected.kind === "synced"
        ? parseLrc(selected.text)
        : null,
    [selected],
  );

  if (!selected) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Source
          <select
            aria-label="Lyrics source"
            value={selected.id}
            onChange={(e) => setSelectedId(e.target.value)}
            className="rounded-md border border-border bg-surface px-2 py-1 text-sm text-foreground"
          >
            {lyrics.map((l) => (
              <option key={l.id} value={l.id}>
                {l.source}
                {l.kind === "synced" ? " (synced)" : ""}
              </option>
            ))}
          </select>
        </label>
        {renderVote ? <div>{renderVote(selected)}</div> : null}
      </div>

      {parsed ? (
        <SyncedBody lines={parsed} />
      ) : (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface p-4 text-sm text-foreground">
          {selected.text}
        </pre>
      )}
    </div>
  );
}

function SyncedBody({ lines }: { lines: LrcLine[] }) {
  const [currentMs, setCurrentMs] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [follow, setFollow] = useState(true);

  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLParagraphElement>(null);
  // Set true around a programmatic scroll so its scroll event doesn't read as a
  // manual scroll and disengage follow.
  const autoScrollingRef = useRef(false);

  const active = activeLineIndex(lines, currentMs);
  const duration = lines[lines.length - 1].timeMs + TICK_MS;

  // Virtual clock: advance while playing, stop at the end.
  useEffect(() => {
    if (!playing) return;
    const handle = setInterval(() => {
      setCurrentMs((ms) => {
        const next = ms + TICK_MS;
        if (next >= duration) {
          setPlaying(false);
          return duration;
        }
        return next;
      });
    }, TICK_MS);
    return () => clearInterval(handle);
  }, [playing, duration]);

  // Autoscroll the active line to centre while following.
  useEffect(() => {
    if (!follow || active < 0) return;
    const el = activeRef.current;
    if (!el) return;
    autoScrollingRef.current = true;
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    const handle = setTimeout(() => {
      autoScrollingRef.current = false;
    }, 0);
    return () => clearTimeout(handle);
  }, [active, follow]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        <input
          type="range"
          aria-label="Seek"
          min={0}
          max={duration}
          value={currentMs}
          onChange={(e) => setCurrentMs(Number(e.target.value))}
          className="flex-1"
        />
        <Button
          variant={follow ? "primary" : "ghost"}
          aria-pressed={follow}
          onClick={() => setFollow(true)}
        >
          Follow
        </Button>
      </div>

      <div
        ref={containerRef}
        data-testid="lyrics-scroll"
        onScroll={() => {
          if (!autoScrollingRef.current) setFollow(false);
        }}
        className="max-h-96 overflow-auto rounded-lg border border-border bg-surface p-4"
      >
        {lines.map((line, i) => (
          <p
            key={`${line.timeMs}-${i}`}
            ref={i === active ? activeRef : undefined}
            data-active={i === active}
            className={`py-1 text-sm transition-colors ${
              i === active
                ? "font-medium text-foreground"
                : "text-muted-foreground"
            }`}
          >
            {line.text || " "}
          </p>
        ))}
      </div>
    </div>
  );
}
