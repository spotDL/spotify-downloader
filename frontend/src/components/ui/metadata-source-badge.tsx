import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { MetadataSourceName } from "@/types";

// Source colors and labels
const sourceConfig: Record<
  MetadataSourceName,
  { label: string; color: string; bgColor: string }
> = {
  spotify: {
    label: "Spotify",
    color: "#1db954",
    bgColor: "rgba(29, 185, 84, 0.1)",
  },
  musicbrainz: {
    label: "MusicBrainz",
    color: "#ba478f",
    bgColor: "rgba(186, 71, 143, 0.1)",
  },
  discogs: {
    label: "Discogs",
    color: "#ff5500",
    bgColor: "rgba(255, 85, 0, 0.1)",
  },
  deezer: {
    label: "Deezer",
    color: "#a238ff",
    bgColor: "rgba(162, 56, 255, 0.1)",
  },
  apple_music: {
    label: "Apple Music",
    color: "#fc3c44",
    bgColor: "rgba(252, 60, 68, 0.1)",
  },
};

export interface MetadataSourceBadgeProps {
  /** The data source */
  source: MetadataSourceName;
  /** Optional confidence score (0-100) */
  confidence?: number;
  /** Size variant */
  size?: "sm" | "md";
  /** Additional class names */
  className?: string;
}

export function MetadataSourceBadge({
  source,
  confidence,
  size = "sm",
  className,
}: MetadataSourceBadgeProps) {
  const config = sourceConfig[source];

  if (!config) {
    return null;
  }

  const sizeClasses = {
    sm: "text-[10px] px-1.5 py-0.5",
    md: "text-xs px-2 py-1",
  };

  return (
    <span
      className={twMerge(
        clsx(
          "metadata-source-badge inline-flex items-center gap-1",
          "font-medium uppercase tracking-wide rounded-full",
          sizeClasses[size]
        ),
        className
      )}
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
      title={
        confidence !== undefined
          ? `${config.label} (${confidence}% confidence)`
          : config.label
      }
    >
      {config.label}
      {confidence !== undefined && (
        <span className="opacity-60">{confidence}%</span>
      )}
    </span>
  );
}

/**
 * Display a metadata field with its source
 */
export interface MetadataFieldProps {
  /** Field label */
  label: string;
  /** Field value */
  value: React.ReactNode;
  /** Source of the data */
  source?: MetadataSourceName;
  /** Confidence score (0-100) */
  confidence?: number;
  /** Additional class names */
  className?: string;
}

export function MetadataField({
  label,
  value,
  source,
  confidence,
  className,
}: MetadataFieldProps) {
  return (
    <div className={twMerge("flex flex-col gap-1", className)}>
      <div className="flex items-center gap-2">
        <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wide">
          {label}
        </span>
        {source && (
          <MetadataSourceBadge source={source} confidence={confidence} size="sm" />
        )}
      </div>
      <div className="text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

/**
 * Grid layout for metadata fields
 */
export interface MetadataGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
  className?: string;
}

export function MetadataGrid({
  children,
  columns = 2,
  className,
}: MetadataGridProps) {
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={twMerge(clsx("grid gap-4", gridCols[columns]), className)}>
      {children}
    </div>
  );
}

/**
 * Collapsible panel for technical metadata
 */
export interface MetadataPanelProps {
  /** Panel title */
  title: string;
  /** Whether the panel is initially open */
  defaultOpen?: boolean;
  /** Panel content */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

export function MetadataPanel({
  title,
  defaultOpen = false,
  children,
  className,
}: MetadataPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={twMerge(
        clsx(
          "bg-[var(--bg-panel)] border border-[var(--color-border-subtle)]",
          "rounded-xl overflow-hidden"
        ),
        className
      )}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          "w-full flex items-center justify-between px-4 py-3",
          "text-left text-sm font-medium text-[var(--color-text-primary)]",
          "hover:bg-[var(--bg-hover)]",
          "transition-colors duration-150"
        )}
      >
        {title}
        <svg
          className={clsx(
            "w-4 h-4 text-[var(--color-text-muted)]",
            "transition-transform duration-200",
            isOpen && "rotate-180"
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-4 py-4 border-t border-[var(--color-border-subtle)]">
          {children}
        </div>
      )}
    </div>
  );
}

// Required useState import
import { useState } from "react";

export default MetadataSourceBadge;
