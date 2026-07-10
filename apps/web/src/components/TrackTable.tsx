import { Link } from "@tanstack/react-router";
import type { TrackOut } from "../api/generated/types.gen";
import { formatDuration, joinArtists } from "../lib/format";
import { NoteIcon, PlayIcon } from "./icons";

// A track listing (mockup `.trow` rows) for the album/playlist pages: index,
// mini cover, title + artists, duration, and a play affordance — each row links
// to the canonical track page.
export function TrackTable({ tracks }: { tracks: TrackOut[] }) {
  return (
    <div className="flex flex-col rounded-card border border-line-soft bg-surface p-2">
      {tracks.map((track, i) => (
        <Link
          key={track.id}
          to="/tracks/$trackId"
          params={{ trackId: track.id }}
          className="group grid grid-cols-[28px_40px_1fr_auto_auto] items-center gap-3.5 rounded-lg px-2.5 py-2 transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald"
        >
          <span className="text-right font-mono text-xs text-muted tabular-nums">
            {track.track_number ?? i + 1}
          </span>
          <span className="size-9 overflow-hidden rounded ring-1 ring-white/5">
            {track.album?.cover_url ? (
              <img src={track.album.cover_url} alt="" className="size-full object-cover" />
            ) : (
              <span className="grid size-full place-items-center bg-elevated text-muted">
                <NoteIcon className="size-4" />
              </span>
            )}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-[13px] font-medium text-fg">
              {track.name}
            </span>
            {track.artists.length > 0 ? (
              <span className="block truncate text-[11px] text-muted">
                {joinArtists(track.artists)}
              </span>
            ) : null}
          </span>
          <span className="font-mono text-xs text-muted tabular-nums">
            {formatDuration(track.duration_ms)}
          </span>
          <PlayIcon className="size-4 text-muted transition-colors group-hover:text-emerald" />
        </Link>
      ))}
    </div>
  );
}
