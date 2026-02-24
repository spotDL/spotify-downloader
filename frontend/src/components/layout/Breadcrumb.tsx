import { Link } from "@tanstack/react-router";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { useQuery } from "@tanstack/react-query";
import { 
  entityKeys, 
  getSongById, 
  getAlbumById, 
  getArtistById, 
  getPlaylistById, 
  isUuid 
} from "@/api/entities";
import type { BreadcrumbItem } from "@/types";

// Home icon
const HomeIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

// Chevron separator
const ChevronIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

export interface BreadcrumbProps {
  /** Breadcrumb items */
  items: BreadcrumbItem[];
  /** Show home icon as first item */
  showHome?: boolean;
  /** Home link path */
  homePath?: string;
  /** Additional class names */
  className?: string;
  /** Separator element */
  separator?: React.ReactNode;
  /** Maximum items to show before collapsing */
  maxItems?: number;
}

export function Breadcrumb({
  items,
  showHome = true,
  homePath = "/",
  className,
  separator = <ChevronIcon />,
  maxItems,
}: BreadcrumbProps) {
  // Collapse items if needed
  const displayItems = maxItems && items.length > maxItems
    ? [
        items[0],
        { label: "...", href: undefined },
        ...items.slice(-(maxItems - 2)),
      ]
    : items;

  return (
    <nav aria-label="Breadcrumb" className={twMerge("breadcrumb", className)}>
      <ol className="flex items-center gap-2 text-sm">
        {/* Home link */}
        {showHome && (
          <>
            <li>
              <Link
                to={homePath}
                className={clsx(
                  "breadcrumb-item flex items-center",
                  "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
                  "transition-colors duration-150"
                )}
                aria-label="Home"
              >
                <HomeIcon />
              </Link>
            </li>
            {items.length > 0 && (
              <li className="breadcrumb-separator text-[var(--color-text-dim)]">
                {separator}
              </li>
            )}
          </>
        )}

        {/* Breadcrumb items */}
        {displayItems.map((item, index) => {
          const isLast = index === displayItems.length - 1;
          const isEllipsis = item.label === "...";

          return (
            <li key={index} className="flex items-center gap-2">
              {isEllipsis ? (
                <span className="text-[var(--color-text-dim)]">...</span>
              ) : item.href && !isLast ? (
                <Link
                  to={item.href}
                  className={clsx(
                    "breadcrumb-item flex items-center gap-1.5",
                    "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
                    "transition-colors duration-150"
                  )}
                >
                  {item.icon && <item.icon className="w-4 h-4" />}
                  <span className="max-w-[150px] truncate">{item.label}</span>
                </Link>
              ) : (
                <span
                  className={clsx(
                    "breadcrumb-item flex items-center gap-1.5",
                    isLast
                      ? "text-[var(--color-text-primary)] font-medium"
                      : "text-[var(--color-text-muted)]"
                  )}
                  aria-current={isLast ? "page" : undefined}
                >
                  {item.icon && <item.icon className="w-4 h-4" />}
                  <span className="max-w-[200px] truncate">{item.label}</span>
                </span>
              )}

              {/* Separator */}
              {!isLast && (
                <span className="breadcrumb-separator text-[var(--color-text-dim)]">
                  {separator}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/**
 * Component to display a dynamic entity label using React Query
 */
function DynamicEntityLabel({ 
  type, 
  id, 
  fallback 
}: { 
  type: string; 
  id: string; 
  fallback: string; 
}) {
  const { data } = useQuery({
    queryKey: 
      type === 'song' ? entityKeys.song(id) :
      type === 'album' ? entityKeys.album(id) :
      type === 'artist' ? entityKeys.artist(id) :
      entityKeys.playlist(id),
    queryFn: async () => {
      if (type === 'song') return getSongById(id);
      if (type === 'album') return getAlbumById(id);
      if (type === 'artist') return getArtistById(id);
      return getPlaylistById(id);
    },
    enabled: isUuid(id) && ['song', 'album', 'artist', 'playlist'].includes(type),
    staleTime: 1000 * 60 * 5,
  });

  if (data && 'name' in data) {
    return <span className="animate-fade-in">{data.name}</span>;
  }
  
  return <span>{fallback}</span>;
}

/**
 * Build breadcrumb items from a route path
 */
export function buildBreadcrumbsFromPath(
  pathname: string,
  labelMap?: Record<string, string>
): BreadcrumbItem[] {
  const segments = pathname.split("/").filter(Boolean);
  const items: BreadcrumbItem[] = [];
  let currentPath = "";

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    currentPath += `/${segment}`;
    
    let href: string | undefined = currentPath;
    const prevSegment = i > 0 ? segments[i - 1] : null;
    const nextSegment = i + 1 < segments.length ? segments[i + 1] : null;

    // Make intermediate entity segments (e.g., /song when followed by an ID) unclickable
    if (
      ["song", "album", "artist", "playlist"].includes(segment) &&
      nextSegment &&
      isUuid(nextSegment)
    ) {
      href = undefined;
    }

    let label: React.ReactNode = labelMap?.[segment];
    if (!label) {
      if (prevSegment && ["song", "album", "artist", "playlist"].includes(prevSegment) && isUuid(segment)) {
        label = <DynamicEntityLabel type={prevSegment} id={segment} fallback={formatSegmentLabel(segment)} />;
      } else {
        label = formatSegmentLabel(segment);
      }
    }

    items.push({ label, href });
  }

  return items;
}

/**
 * Format a URL segment as a human-readable label
 */
function formatSegmentLabel(segment: string): string {
  // Check if it's a UUID (skip formatting)
  if (isUuid(segment)) {
    return segment.slice(0, 8) + "...";
  }

  // Convert kebab-case or snake_case to Title Case
  return segment
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default Breadcrumb;
