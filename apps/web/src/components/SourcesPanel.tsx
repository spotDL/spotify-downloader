import { ExternalLink } from "lucide-react";
import type {
  EntityType,
  MetadataSourceOut,
} from "../api/generated/types.gen";
import { useEntitySources } from "../api/queries";
import { formatFollowers } from "../lib/format";
import { entityProviderUrl, providerMeta } from "../lib/providers";
import { Card } from "./Card";
import { Skeleton } from "./ui/skeleton";

// The ONE merged Sources panel (Layout v2): one row per provider snapshot behind
// the canonical entity, folding the old "Reach across platforms" + "Metadata
// sources" duplication into a single provenance list. Each row: an identity dot,
// the provider name, its primary count (follower/fan, or the entity-appropriate
// fact) in mono, a ★ popularity chip in the community/emerald voice when the
// provider reports a canonical 0–100 score, and an external link when we can
// build a public URL.

/** Only surface a canonical 0–100 popularity (a Deezer fan-count can exceed 100). */
function popularityScore(source: MetadataSourceOut): number | null {
  const p = source.popularity;
  return p != null && p >= 0 && p <= 100 ? p : null;
}

/**
 * The provider's headline mono fact for this entity type: the reach count for an
 * artist, the label for an album, the ISRC for a track. Falls back to a
 * Last.fm-style listener count when that's all a provider carries.
 */
function primaryFact(
  entityType: EntityType,
  source: MetadataSourceOut,
): string | null {
  if (entityType === "artist" && source.followers != null) {
    return formatFollowers(source.followers);
  }
  if (entityType === "album") {
    if (source.label) return source.label;
    if (source.year != null) return String(source.year);
  }
  if (entityType === "track" && source.isrc) return source.isrc;
  if (source.followers != null) return formatFollowers(source.followers);
  if (source.listeners != null) return `${formatFollowers(source.listeners)} listeners`;
  return null;
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
      <Card title="Sources">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-6" />
          <Skeleton className="h-6" />
        </div>
      </Card>
    );
  }

  if (query.isError) {
    return (
      <Card title="Sources">
        <p className="text-[12px] text-muted-foreground">Couldn't load sources.</p>
      </Card>
    );
  }

  const sources = query.data.sources;
  // Empty (no providers) → omit the panel entirely.
  if (sources.length === 0) return null;

  return (
    <Card title="Sources" action={String(sources.length)}>
      <div className="flex flex-col">
        {sources.map((source, i) => {
          const meta = providerMeta(source.provider);
          const fact = primaryFact(entityType, source);
          const popularity = popularityScore(source);
          const url = entityProviderUrl(
            source.provider,
            entityType,
            source.provider_entity_id,
          );
          return (
            <div
              key={`${source.provider}-${i}`}
              className="flex items-center gap-2.5 border-b border-border py-2 last:border-b-0"
            >
              <span
                className={`size-2 shrink-0 rounded-full ${meta.dotClass}`}
                aria-hidden
              />
              <span className="min-w-0 flex-1 truncate text-[12.5px] font-medium text-foreground">
                {meta.label}
              </span>
              {fact ? (
                <span className="shrink-0 font-mono tnum text-[11.5px] text-muted-foreground">
                  {fact}
                </span>
              ) : null}
              {popularity != null ? (
                <span className="shrink-0 font-mono tnum text-[11.5px] font-medium text-secondary">
                  ★ {popularity}
                </span>
              ) : null}
              {url ? (
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Open on ${meta.label}`}
                  className="shrink-0 text-faint transition-colors hover:text-secondary"
                >
                  <ExternalLink className="size-3.5" />
                </a>
              ) : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
