import { Link } from "@tanstack/react-router";
import type { TrackOut } from "../api/generated/types.gen";
import { formatDuration, joinArtists } from "../lib/format";
import { NoteIcon, PlayIcon } from "./icons";

// A track listing for the album/playlist pages: index, mini cover, title +
// artists, duration, and a play affordance — each row links to the canonical
// track page.
export function TrackTable({ tracks }: { tracks: TrackOut[] }) {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-surface p-2">
      {tracks.map((track, i) => (
        <Link
          key={track.id}
          to="/tracks/$trackId"
          params={{ trackId: track.id }}
          className="group grid grid-cols-[28px_40px_1fr_auto_auto] items-center gap-3.5 rounded-md px-2.5 py-2 transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="text-right font-mono text-xs text-muted-foreground tnum">
            {track.track_number ?? i + 1}
          </span>
          <span className="size-9 overflow-hidden rounded border border-border">
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
          <span className="font-mono text-xs text-muted-foreground tnum">
            {formatDuration(track.duration_ms)}
          </span>
          <PlayIcon className="size-4 text-muted-foreground transition-colors group-hover:text-primary" />
        </Link>
      ))}
    </div>
  );
}
