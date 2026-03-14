/**
 * Entity ID resolution logic.
 *
 * Handles resolving external IDs (Spotify IDs, URLs, search queries)
 * to canonical internal entity UUIDs via the discover endpoint.
 */

import { apiClient } from "./client";
import type { DiscoverApiResponse, EntityApiResponse } from "./entity-mappers";

export type DiscoverEntityType = EntityApiResponse["type"];

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const entityIdResolutionCache = new Map<string, string>();

export function isUuid(value: string): boolean {
  return UUID_REGEX.test(value);
}

export function buildCandidateUrls(entityId: string, expectedType?: DiscoverEntityType): string[] {
  if (!entityId || entityId.includes("/") || entityId.includes(":")) {
    return [];
  }

  const candidates = new Set<string>();
  const add = (url: string) => candidates.add(url);
  const type = expectedType ?? "track";

  if (type === "track") {
    add(`https://open.spotify.com/track/${entityId}`);
    add(`https://www.youtube.com/watch?v=${entityId}`);
    add(`https://music.youtube.com/watch?v=${entityId}`);
  }
  if (type === "album") {
    add(`https://open.spotify.com/album/${entityId}`);
    add(`https://music.youtube.com/browse/${entityId}`);
  }
  if (type === "artist") {
    add(`https://open.spotify.com/artist/${entityId}`);
    add(`https://music.youtube.com/channel/${entityId}`);
    add(`https://music.youtube.com/browse/${entityId}`);
  }
  if (type === "playlist") {
    add(`https://open.spotify.com/playlist/${entityId}`);
    add(`https://www.youtube.com/playlist?list=${entityId}`);
    add(`https://music.youtube.com/playlist?list=${entityId}`);
    add(`https://music.youtube.com/browse/${entityId}`);
  }

  if (!expectedType) {
    add(`https://open.spotify.com/track/${entityId}`);
    add(`https://open.spotify.com/album/${entityId}`);
    add(`https://open.spotify.com/artist/${entityId}`);
    add(`https://open.spotify.com/playlist/${entityId}`);
  }

  return Array.from(candidates);
}

export function pickDiscoveredEntity(
  entities: EntityApiResponse[],
  expectedType?: DiscoverEntityType
): EntityApiResponse | null {
  if (!entities.length) return null;
  if (expectedType) {
    return entities.find((entity) => entity.type === expectedType) ?? null;
  }
  return entities[0];
}

export async function discoverEntity(
  payload: { query?: string; url?: string; types?: string[]; limit?: number },
  expectedType?: DiscoverEntityType
): Promise<EntityApiResponse | null> {
  try {
    const response = await apiClient.post<DiscoverApiResponse>("/entities/discover", payload);
    return pickDiscoveredEntity(response.data.entities, expectedType);
  } catch {
    return null;
  }
}

export async function resolveEntityId(
  entityIdOrExternalId: string,
  expectedType?: DiscoverEntityType
): Promise<string> {
  if (!entityIdOrExternalId) {
    throw new Error("Entity ID is required");
  }

  if (isUuid(entityIdOrExternalId)) {
    return entityIdOrExternalId;
  }

  const cacheKey = `${expectedType ?? "any"}:${entityIdOrExternalId}`;
  const cached = entityIdResolutionCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const isUrl = entityIdOrExternalId.startsWith("http://") || entityIdOrExternalId.startsWith("https://");

  const byUrl = isUrl
    ? await discoverEntity(
      {
        url: entityIdOrExternalId,
        types: expectedType ? [expectedType] : undefined,
        limit: 20,
      },
      expectedType
    )
    : null;
  if (byUrl) {
    entityIdResolutionCache.set(cacheKey, byUrl.id);
    return byUrl.id;
  }

  const byQuery = await discoverEntity(
    {
      query: entityIdOrExternalId,
      types: expectedType ? [expectedType] : undefined,
      limit: 20,
    },
    expectedType
  );
  if (byQuery) {
    entityIdResolutionCache.set(cacheKey, byQuery.id);
    return byQuery.id;
  }

  const fallbackUrls = buildCandidateUrls(entityIdOrExternalId, expectedType);
  for (const url of fallbackUrls) {
    const found = await discoverEntity(
      { url, types: expectedType ? [expectedType] : undefined, limit: 20 },
      expectedType
    );
    if (found) {
      entityIdResolutionCache.set(cacheKey, found.id);
      return found.id;
    }
  }

  throw new Error(
    `Could not resolve '${entityIdOrExternalId}' to a canonical entity ID`
  );
}
