import type { ReactNode } from "react";
import type {
  EntityType,
  MetadataSourceOut,
} from "../api/generated/types.gen";
import { useEntitySources } from "../api/queries";
import { formatFollowers } from "../lib/format";
import { providerMeta } from "../lib/providers";
import { Card } from "./Card";

// The "Metadata sources" panel + a cross-platform "Reach" stat card. Both read
// the same `/{entity}/{id}/sources` provenance (the merged canonical row is
// Spotify-first; this shows which provider contributed which field). Data-driven:
// each self-omits when there's nothing to show, so routes can mount them
// unconditionally in a sidebar.

/** Only surface a canonical 0–100 popularity (a Deezer fan-count can exceed 100). */
function popularityScore(source: MetadataSourceOut): number | null {
  const p = source.popularity;
  return p != null && p >= 0 && p <= 100 ? p : null;
}

// A small brand dot beside a label — the shared source/reach row prefix.
function ProviderTag({ provider }: { provider: string }) {
  const meta = providerMeta(provider);
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span className={`size-2 shrink-0 rounded-full ${meta.dotClass}`} aria-hidden />
      <span className="truncate text-[12.5px] font-medium text-fg">{meta.label}</span>
    </span>
  );
}

// The mono "what this provider contributed" summary, per entity type.
function sourceMetric(
  entityType: EntityType,
  source: MetadataSourceOut,
): ReactNode {
  const parts: string[] = [];
  const popularity = popularityScore(source);
  if (entityType === "artist") {
    if (source.followers != null) parts.push(formatFollowers(source.followers));
    if (popularity != null) parts.push(`★ ${popularity}`);
  } else if (entityType === "album") {
    if (source.label) parts.push(source.label);
    if (popularity != null) parts.push(`★ ${popularity}`);
  } else {
    // track (and any other): ISRC + popularity
    if (source.isrc) parts.push(source.isrc);
    if (popularity != null) parts.push(`★ ${popularity}`);
  }
  if (parts.length === 0) return null;
  return (
    <span className="shrink-0 font-mono tabular-nums text-[11.5px] text-ink-2">
      {parts.join(" · ")}
    </span>
  );
}

/** The provenance list: one row per provider snapshot behind the canonical entity. */
export function SourcesPanel({
  entityType,
  id,
}: {
  entityType: EntityType;
  id: string;
}) {
  const query = useEntitySources(entityType, id);

  if (query.isPending) {
    return (
      <Card title="Metadata sources">
        <div className="flex flex-col gap-2">
          <div className="shimmer h-6 rounded-lg" />
          <div className="shimmer h-6 rounded-lg" />
        </div>
      </Card>
    );
  }

  if (query.isError) {
    return (
      <Card title="Metadata sources">
        <p className="text-[12px] text-muted">Couldn't load sources.</p>
      </Card>
    );
  }

  const sources = query.data.sources;
  // Empty (no providers) → omit the panel entirely.
  if (sources.length === 0) return null;

  return (
    <Card title="Metadata sources" action={`${sources.length} sources`}>
      <div className="flex flex-col">
        {sources.map((source, i) => (
          <div
            key={`${source.provider}-${i}`}
            className="flex items-center justify-between gap-4 border-b border-line-soft py-2 last:border-b-0"
          >
            <ProviderTag provider={source.provider} />
            {sourceMetric(entityType, source) ?? (
              <span className="font-mono text-[11px] text-muted">
                {source.entity_type}
              </span>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

/**
 * "Reach across platforms": a compact, honest comparison of provider-reported
 * follower/fan counts (NOT licensed play counts). Artist-only; renders whenever
 * at least one source carries a followers value.
 */
export function StatsCard({ id }: { id: string }) {
  const query = useEntitySources("artist", id);

  const withFollowers =
    query.data?.sources.filter((s) => s.followers != null) ?? [];
  if (withFollowers.length === 0) return null;

  return (
    <Card title="Reach across platforms">
      <p className="mb-3 text-[11.5px] leading-snug text-muted">
        Provider-reported followers/fans — not licensed play counts.
      </p>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {withFollowers.map((source, i) => (
          <span
            key={`${source.provider}-${i}`}
            className="flex items-center gap-2"
          >
            <span
              className={`size-2 shrink-0 rounded-full ${providerMeta(source.provider).dotClass}`}
              aria-hidden
            />
            <span className="text-[12px] text-ink-2">
              {providerMeta(source.provider).label}
            </span>
            <span className="font-mono tabular-nums text-[13px] font-semibold text-fg">
              {formatFollowers(source.followers)}
            </span>
          </span>
        ))}
      </div>
    </Card>
  );
}
