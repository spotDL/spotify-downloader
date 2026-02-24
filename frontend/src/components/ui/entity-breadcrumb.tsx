import { Link } from "@tanstack/react-router";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { BreadcrumbItem } from "@/types";

export interface EntityBreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

// Home icon
const HomeIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
    />
  </svg>
);

// Chevron separator
const ChevronSeparator = () => (
  <svg
    className="w-4 h-4 text-[var(--color-text-dim)] flex-shrink-0"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

export function EntityBreadcrumb({ items, className }: EntityBreadcrumbProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <nav
      aria-label="Breadcrumb"
      className={twMerge(
        clsx(
          "breadcrumb",
          "flex items-center flex-wrap gap-1.5",
          "text-sm",
          className
        )
      )}
    >
      {/* Home link (always present) */}
      <Link
        to="/"
        className={clsx(
          "breadcrumb-item",
          "flex items-center gap-1",
          "text-[var(--color-text-muted)]",
          "hover:text-[var(--color-text-primary)]",
          "transition-colors duration-150",
          "focus:outline-none focus-visible:ring-2",
          "focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2",
          "focus-visible:ring-offset-[var(--bg-chassis)]",
          "rounded-sm"
        )}
        aria-label="Home"
      >
        <HomeIcon className="w-4 h-4" />
      </Link>

      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        const Icon = item.icon;

        return (
          <div key={index} className="flex items-center gap-1.5">
            {/* Separator */}
            <ChevronSeparator />

            {/* Breadcrumb Item */}
            {isLast || !item.href ? (
              // Current page (not clickable)
              <span
                className={clsx(
                  "breadcrumb-item",
                  "flex items-center gap-1.5",
                  isLast
                    ? "text-[var(--color-text-primary)] font-medium"
                    : "text-[var(--color-text-muted)]",
                  // Truncate long text on mobile
                  "max-w-[150px] sm:max-w-[200px] md:max-w-none truncate"
                )}
                aria-current={isLast ? "page" : undefined}
                title={typeof item.label === 'string' ? item.label : undefined}
              >
                {Icon && <Icon className="w-4 h-4 flex-shrink-0" />}
                <span className="truncate">{item.label}</span>
              </span>
            ) : (
              // Clickable link
              <Link
                to={item.href}
                className={clsx(
                  "breadcrumb-item",
                  "flex items-center gap-1.5",
                  "text-[var(--color-text-muted)]",
                  "hover:text-[var(--color-text-primary)]",
                  "transition-colors duration-150",
                  "focus:outline-none focus-visible:ring-2",
                  "focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2",
                  "focus-visible:ring-offset-[var(--bg-chassis)]",
                  "rounded-sm",
                  // Truncate long text on mobile
                  "max-w-[150px] sm:max-w-[200px] md:max-w-none"
                )}
                title={typeof item.label === 'string' ? item.label : undefined}
              >
                {Icon && <Icon className="w-4 h-4 flex-shrink-0" />}
                <span className="truncate">{item.label}</span>
              </Link>
            )}
          </div>
        );
      })}
    </nav>
  );
}

// Convenience component for common entity breadcrumbs
export interface EntityBreadcrumbPresetProps {
  entityType: "artist" | "album" | "song" | "playlist";
  entityName: string;
  parentEntity?: {
    type: "artist" | "album";
    id: string;
    name: string;
  };
  className?: string;
}

// Entity type icons
const entityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  artist: ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
  ),
  album: ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 14.5c-2.49 0-4.5-2.01-4.5-4.5S9.51 7.5 12 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm0-5.5c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z" />
    </svg>
  ),
  song: ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
    </svg>
  ),
  playlist: ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18c-.31-.11-.65-.18-1-.18-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3V8h3V6h-5z" />
    </svg>
  ),
};


export function EntityBreadcrumbPreset({
  entityType,
  entityName,
  parentEntity,
  className,
}: EntityBreadcrumbPresetProps) {
  const items: BreadcrumbItem[] = [];

  // Add parent entity if present (e.g., artist for album, album for song)
  if (parentEntity) {
    items.push({
      label: parentEntity.name,
      href: `/${parentEntity.type}/${parentEntity.id}`,
      icon: entityIcons[parentEntity.type],
    });
  }

  // Add current entity
  items.push({
    label: entityName,
    icon: entityIcons[entityType],
  });

  return <EntityBreadcrumb items={items} className={className} />;
}

export default EntityBreadcrumb;
