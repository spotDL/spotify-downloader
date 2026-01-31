import { Badge, PlatformBadge } from "@/components/ui";
import type { EntitySearchResult as EntitySearchResultType, EntityType } from "@/types";

interface EntitySearchResultCardProps {
  result: EntitySearchResultType;
}

const entityTypeLabels: Record<EntityType, string> = {
  artist: "Artist",
  album: "Album",
  playlist: "Playlist",
  track: "Song",
};

const entityRoutes: Record<EntityType, string> = {
  artist: "/artist",
  album: "/album",
  playlist: "/playlist",
  track: "/song",
};

export function EntitySearchResultCard({ result }: EntitySearchResultCardProps) {
  const routeBase = entityRoutes[result.entity_type];
  const href = `${routeBase}/${result.platform}/${result.id}`;

  return (
    <a
      href={href}
      className="group relative flex items-center gap-4 p-4 bg-zinc-900/50 hover:bg-zinc-800/70 border border-zinc-800/50 hover:border-zinc-700/50 rounded-xl cursor-pointer transition-all duration-200 hover:shadow-lg hover:shadow-black/20"
    >
      {/* Image */}
      <div className="relative w-16 h-16 shrink-0">
        {result.image_url ? (
          <img
            src={result.image_url}
            alt={result.name}
            className={`w-16 h-16 object-cover shadow-md group-hover:shadow-lg transition-shadow duration-200 ${
              result.entity_type === "artist" ? "rounded-full" : "rounded-lg"
            }`}
          />
        ) : (
          <div
            className={`w-16 h-16 bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center shadow-md ${
              result.entity_type === "artist" ? "rounded-full" : "rounded-lg"
            }`}
          >
            <EntityIcon type={result.entity_type} />
          </div>
        )}

        {/* Entity type badge */}
        <div className="absolute -bottom-1 -right-1">
          <Badge variant="default" size="sm" className="text-[10px] px-1.5 py-0.5">
            {entityTypeLabels[result.entity_type]}
          </Badge>
        </div>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-zinc-100 truncate group-hover:text-white transition-colors">
          {result.name}
        </h3>
        {result.subtitle && (
          <p className="text-sm text-zinc-400 truncate mt-0.5">{result.subtitle}</p>
        )}
        <div className="mt-2">
          <PlatformBadge platform={result.platform as any} />
        </div>
      </div>

      {/* Arrow */}
      <svg
        className="w-5 h-5 text-zinc-600 group-hover:text-zinc-400 group-hover:translate-x-0.5 transition-all duration-200 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </a>
  );
}

function EntityIcon({ type }: { type: EntityType }) {
  switch (type) {
    case "artist":
      return (
        <svg className="w-7 h-7 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      );
    case "album":
      return (
        <svg className="w-7 h-7 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      );
    case "playlist":
      return (
        <svg className="w-7 h-7 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      );
    case "track":
    default:
      return (
        <svg className="w-7 h-7 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
        </svg>
      );
  }
}
