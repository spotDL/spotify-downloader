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
  onSelect,
}: {
  type: EntityType;
  id: string;
  name: string;
  subtitle?: string;
  imageUrl?: string | null;
  className?: string;
  /** Overrides the default link navigation (e.g. resolve-then-navigate). */
  onSelect?: () => void;
}) {
  return (
    <a
      href={`/${ROUTE_SEGMENT[type]}/${id}`}
      onClick={
        onSelect
          ? (e) => {
              e.preventDefault();
              onSelect();
            }
          : undefined
      }
      className={`flex items-center gap-3 rounded-card border border-line-soft bg-elevated p-3 transition-colors hover:bg-hover ${className}`}
    >
      {imageUrl != null && imageUrl !== "" ? (
        <img
          src={imageUrl}
          alt=""
          className="size-12 shrink-0 rounded object-cover"
          loading="lazy"
        />
      ) : (
        <div
          aria-hidden
          className="flex size-12 shrink-0 items-center justify-center rounded bg-surface text-muted"
        >
          <span className="text-lg leading-none">♪</span>
        </div>
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
