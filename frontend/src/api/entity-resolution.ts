/**
 * Entity ID resolution logic.
 *
 * Resolves external IDs (Spotify IDs, URLs, etc.) to canonical internal
 * entity UUIDs via the backend resolve endpoint.
 */

import { apiClient } from "./client";
import type { EntityApiResponse } from "./entity-mappers";

export type DiscoverEntityType = EntityApiResponse["type"];

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const entityIdResolutionCache = new Map<string, string>();

export function isUuid(value: string): boolean {
  return UUID_REGEX.test(value);
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

  const params: Record<string, string> = { id: entityIdOrExternalId };
  if (expectedType) {
    params.type = expectedType;
  }

  const response = await apiClient.get<{ entity_id: string }>("/entities/resolve", { params });
  const resolvedId = response.data.entity_id;

  entityIdResolutionCache.set(cacheKey, resolvedId);
  return resolvedId;
}
