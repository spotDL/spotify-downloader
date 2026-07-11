import { useState } from "react";
import { Link } from "@tanstack/react-router";
import type { TrackOut } from "../api/generated/types.gen";
import { formatDuration, joinArtists } from "../lib/format";
import { NoteIcon, PlayIcon } from "./icons";

// The reading-width cap for entity track lists (Layout v2 rule 1) and the number
// of rows shown before the "Show all N" expander (rule 2).
const COLLAPSED_ROWS = 10;

// A dense (48px-row) track listing for the album/playlist/artist pages: a leading
// number, a mini cover, a single-line title + artists, a mono duration, and a
// hover-revealed play affordance — each row links to the canonical track page.
//
// `numbering` picks what the leading number means:
//   "track_number" — each track's own album track number (albums, where the
//     position IS the track number; falls back to the row index if unset).
//   "index" — the 1..N position within THIS list (artist top-tracks and playlist
//     position, whose tracks each carry a source album's track_number that would
//     render as a nonsensical "1, 10, 3, 1…" sequence).
export function TrackTable({
  tracks,
  numbering = "track_number",
}: {
  tracks: TrackOut[];
  numbering?: "track_number" | "index";
}) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? tracks : tracks.slice(0, COLLAPSED_ROWS);
  const hidden = tracks.length - visible.length;

  return (
    <div className="max-w-3xl">
      <div className="flex flex-col rounded-lg border border-border bg-card p-1.5">
        {visible.map((track, i) => (
          <Link
            key={track.id}
            to="/tracks/$trackId"
            params={{ trackId: track.id }}
            className="group grid h-12 grid-cols-[1.75rem_2.5rem_1fr_auto] items-center gap-3 rounded-md px-2 transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="text-right font-mono text-xs text-faint tnum">
              {numbering === "index" ? i + 1 : (track.track_number ?? i + 1)}
            </span>
            <span className="size-10 overflow-hidden rounded border border-border">
              {track.cover_url ?? track.album?.cover_url ? (
                <img
                  src={track.cover_url ?? track.album?.cover_url ?? undefined}
                  alt=""
                  className="size-full object-cover"
                />
              ) : (
                <span className="grid size-full place-items-center bg-elevated text-faint">
                  <NoteIcon className="size-4" />
                </span>
              )}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-medium text-foreground">
                {track.name}
              </span>
              {track.artists.length > 0 ? (
                <span className="block truncate text-[11px] text-muted-foreground">
                  {joinArtists(track.artists)}
                </span>
              ) : null}
            </span>
            <span className="flex items-center gap-3">
              <span className="font-mono text-xs text-muted-foreground tnum">
                {formatDuration(track.duration_ms)}
              </span>
              <PlayIcon className="size-4 text-faint opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" />
            </span>
          </Link>
        ))}
      </div>
      {hidden > 0 ? (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="mt-2 w-full rounded-md px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Show all {tracks.length}
        </button>
      ) : null}
    </div>
  );
}
