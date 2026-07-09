import type { EntityType } from "../api/generated/types.gen";
import { Badge } from "./Badge";

// CONTRACT H — EntityCard. Cover art, title, subtitle (artists/owner), and a
// type badge, linking to the entity route. Used across search results and the
// album/artist/playlist track lists.

const ROUTE_SEGMENT: Record<EntityType, string> = {
  track: "tracks",
  album: "albums",
  artist: "artists",
  playlist: "playlists",
};

export function EntityCard({
  type,
  id,
  name,
  subtitle,
  imageUrl,
  className = "",
}: {
  type: EntityType;
  id: string;
  name: string;
  subtitle?: string;
  imageUrl?: string | null;
  className?: string;
}) {
  return (
    <a
      href={`/${ROUTE_SEGMENT[type]}/${id}`}
      className={`flex items-center gap-3 rounded-card border border-black/10 bg-surface p-3 transition-colors hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/5 ${className}`}
    >
      {imageUrl != null && imageUrl !== "" ? (
        <img
          src={imageUrl}
          alt=""
          className="size-12 shrink-0 rounded object-cover"
          loading="lazy"
        />
      ) : (
        <div className="size-12 shrink-0 rounded bg-black/10 dark:bg-white/10" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate text-sm font-medium text-fg">{name}</span>
        {subtitle !== undefined && subtitle !== "" ? (
          <span className="truncate text-xs text-muted">{subtitle}</span>
        ) : null}
      </div>
      <Badge tone="muted" className="capitalize">
        {type}
      </Badge>
    </a>
  );
}
