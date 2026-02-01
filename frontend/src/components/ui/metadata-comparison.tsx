import { useMemo } from "react";
import { clsx } from "clsx";
import type {
  MetadataSnapshot,
  ComparisonRow,
  NormalizedMetadata,
} from "@/types/metadata";

// Re-export these for convenience
export type { ComparisonRow };

interface MetadataComparisonTableProps {
  snapshots: MetadataSnapshot[];
  className?: string;
  showOnlyDifferences?: boolean;
  categories?: Array<"basic" | "identifiers" | "audio" | "credits" | "classification">;
}

const SOURCE_LABELS: Record<string, string> = {
  spotify: "Spotify",
  musicbrainz: "MusicBrainz",
  discogs: "Discogs",
  youtube_music: "YouTube Music",
  deezer: "Deezer",
  apple_music: "Apple Music",
};

const SOURCE_COLORS: Record<string, string> = {
  spotify: "text-green-500",
  musicbrainz: "text-yellow-500",
  discogs: "text-orange-500",
  youtube_music: "text-red-500",
  deezer: "text-purple-500",
  apple_music: "text-pink-500",
};

const FIELDS_CONFIG: Array<{
  key: keyof NormalizedMetadata;
  label: string;
  category: "basic" | "identifiers" | "audio" | "credits" | "classification";
  format?: (value: unknown) => string;
}> = [
  { key: "name", label: "Track Name", category: "basic" },
  {
    key: "artists",
    label: "Artists",
    category: "basic",
    format: (v) => (Array.isArray(v) ? v.join(", ") : String(v ?? "-")),
  },
  { key: "album_name", label: "Album", category: "basic" },
  { key: "release_date", label: "Release Date", category: "basic" },
  { key: "year", label: "Year", category: "basic" },
  { key: "isrc", label: "ISRC", category: "identifiers" },
  { key: "musicbrainz_id", label: "MusicBrainz ID", category: "identifiers" },
  { key: "discogs_id", label: "Discogs ID", category: "identifiers" },
  {
    key: "genres",
    label: "Genres",
    category: "classification",
    format: (v) => (Array.isArray(v) ? v.join(", ") : String(v ?? "-")),
  },
  {
    key: "styles",
    label: "Styles",
    category: "classification",
    format: (v) => (Array.isArray(v) ? v.join(", ") : String(v ?? "-")),
  },
  {
    key: "explicit",
    label: "Explicit",
    category: "classification",
    format: (v) => (v === true ? "Yes" : v === false ? "No" : "-"),
  },
  { key: "label", label: "Label", category: "credits" },
  {
    key: "producers",
    label: "Producers",
    category: "credits",
    format: (v) => (Array.isArray(v) ? v.join(", ") : String(v ?? "-")),
  },
  {
    key: "writers",
    label: "Writers",
    category: "credits",
    format: (v) => (Array.isArray(v) ? v.join(", ") : String(v ?? "-")),
  },
  {
    key: "bpm",
    label: "BPM",
    category: "audio",
    format: (v) => (typeof v === "number" ? v.toFixed(0) : "-"),
  },
  { key: "key", label: "Key", category: "audio" },
  {
    key: "energy",
    label: "Energy",
    category: "audio",
    format: (v) => (typeof v === "number" ? `${(v * 100).toFixed(0)}%` : "-"),
  },
  {
    key: "danceability",
    label: "Danceability",
    category: "audio",
    format: (v) => (typeof v === "number" ? `${(v * 100).toFixed(0)}%` : "-"),
  },
  {
    key: "valence",
    label: "Valence",
    category: "audio",
    format: (v) => (typeof v === "number" ? `${(v * 100).toFixed(0)}%` : "-"),
  },
  { key: "popularity", label: "Popularity", category: "audio" },
];

function formatValue(value: unknown, formatter?: (v: unknown) => string): string {
  if (formatter) {
    return formatter(value);
  }
  if (value === null || value === undefined) {
    return "-";
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(", ") : "-";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "number") {
    return value.toString();
  }
  return String(value) || "-";
}

function buildComparisonData(
  snapshots: MetadataSnapshot[],
  showOnlyDifferences: boolean,
  categories?: Array<"basic" | "identifiers" | "audio" | "credits" | "classification">
): ComparisonRow[] {
  const rows: ComparisonRow[] = [];

  for (const field of FIELDS_CONFIG) {
    // Filter by category if specified
    if (categories && !categories.includes(field.category)) {
      continue;
    }

    const values = snapshots.map((snapshot) => ({
      source: snapshot.source,
      value: (snapshot.data as Record<string, unknown>)?.[field.key],
    }));

    // Check if values differ
    if (showOnlyDifferences) {
      const formattedValues = values.map((v) => formatValue(v.value, field.format));
      const uniqueValues = new Set(formattedValues);
      if (uniqueValues.size <= 1) {
        continue;
      }
    }

    rows.push({
      field: field.key,
      label: field.label,
      values,
    });
  }

  return rows;
}

/**
 * Table component for comparing metadata across multiple sources side-by-side.
 */
export function MetadataComparisonTable({
  snapshots,
  className,
  showOnlyDifferences = false,
  categories,
}: MetadataComparisonTableProps) {
  const sources = useMemo(() => snapshots.map((s) => s.source), [snapshots]);

  const comparisonData = useMemo(
    () => buildComparisonData(snapshots, showOnlyDifferences, categories),
    [snapshots, showOnlyDifferences, categories]
  );

  if (snapshots.length === 0) {
    return null;
  }

  if (comparisonData.length === 0) {
    return (
      <div className={clsx("p-4 text-center text-[var(--color-text-muted)]", className)}>
        {showOnlyDifferences
          ? "No differences found between sources"
          : "No comparable data available"}
      </div>
    );
  }

  return (
    <div className={clsx("overflow-hidden rounded-lg border border-[var(--border-primary)]", className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[var(--bg-secondary)]">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-[var(--color-text-muted)]">
                Field
              </th>
              {sources.map((source) => (
                <th
                  key={source}
                  className="px-4 py-3 text-left font-medium"
                >
                  <div className={clsx("flex items-center gap-2", SOURCE_COLORS[source] || "text-[var(--color-text-muted)]")}>
                    <SourceIcon source={source} className="w-4 h-4" />
                    <span>{SOURCE_LABELS[source] || source}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-primary)]">
            {comparisonData.map((row) => {
              const fieldConfig = FIELDS_CONFIG.find((f) => f.key === row.field);
              return (
                <tr key={row.field} className="hover:bg-[var(--bg-hover)]">
                  <td className="px-4 py-2 font-medium text-[var(--color-text-secondary)]">
                    {row.label}
                  </td>
                  {sources.map((source) => {
                    const cellData = row.values.find((v) => v.source === source);
                    const formattedValue = formatValue(cellData?.value, fieldConfig?.format);
                    const isEmpty = formattedValue === "-";
                    return (
                      <td
                        key={source}
                        className={clsx(
                          "px-4 py-2",
                          isEmpty
                            ? "text-[var(--color-text-muted)]"
                            : "text-[var(--color-text-primary)]"
                        )}
                      >
                        {formattedValue}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Simple source icon component
interface SourceIconProps {
  source: string;
  className?: string;
}

function SourceIcon({ source, className }: SourceIconProps) {
  const iconMap: Record<string, React.ReactNode> = {
    spotify: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
      </svg>
    ),
    musicbrainz: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" />
      </svg>
    ),
    discogs: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zm0 22.5C6.201 22.5 1.5 17.799 1.5 12S6.201 1.5 12 1.5 22.5 6.201 22.5 12 17.799 22.5 12 22.5zm0-18c-3.59 0-6.5 2.91-6.5 6.5s2.91 6.5 6.5 6.5 6.5-2.91 6.5-6.5-2.91-6.5-6.5-6.5zm0 11.5c-2.761 0-5-2.239-5-5s2.239-5 5-5 5 2.239 5 5-2.239 5-5 5z" />
      </svg>
    ),
  };

  return iconMap[source] || (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

export default MetadataComparisonTable;
