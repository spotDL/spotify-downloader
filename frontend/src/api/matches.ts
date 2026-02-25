import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { FindMatchesResponse, Match, MatchResult } from "@/types";

interface EntityApiResponse {
  id: string;
  type: string;
  name: string;
  canonical: Record<string, unknown>;
}

interface RelationApiResponse {
  id: string;
  from_entity_id: string;
  to_entity_id: string;
  relation_type: string;
  match_score: number | null;
  confidence: number;
  status: string;
  discovered_by: string | null;
  upvotes: number;
  downvotes: number;
  net_votes: number;
  relation_data: Record<string, unknown>;
  target: EntityApiResponse | null;
}

interface RelationsApiResponse {
  entity_id: string;
  relations: RelationApiResponse[];
  total: number;
}

interface DiscoverApiResponse {
  query: string;
  query_type: string;
  entities: EntityApiResponse[];
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function entityToResult(entity: EntityApiResponse): MatchResult {
  const canonical = entity.canonical || {};
  const artists = asStringArray(canonical.artists);
  const artist = asString(canonical.artist, artists[0] || "Unknown");
  return {
    name: entity.name,
    artists: artists.length > 0 ? artists : [artist],
    artist,
    duration: asNumber(canonical.duration, 0),
    platform: asString(canonical.platform, "unknown"),
    platform_id: asString(canonical.platform_id),
    url: asString(canonical.url),
    album_name: asString(canonical.album_name) || null,
    cover_url: asString(canonical.cover_url) || null,
    views: asNumber(canonical.views, 0) || null,
    explicit: Boolean(canonical.explicit),
    verified: Boolean(canonical.verified),
    description: asString(canonical.description) || null,
    site_name: asString(canonical.site_name) || null,
    resolved_via: (asString(canonical.site_name) ? "open_graph" : "provider") as MatchResult["resolved_via"],
  };
}

function relationToMatch(relation: RelationApiResponse, sourceEntity?: EntityApiResponse): Match {
  const targetEntity = relation.target;
  const targetResult = targetEntity ? entityToResult(targetEntity) : {
    name: "Unknown",
    artists: [],
    artist: "Unknown",
    duration: 0,
    platform: "unknown",
    platform_id: "",
    url: "",
    album_name: null,
    cover_url: null,
    views: null,
    explicit: false,
    verified: false,
  };

  const sourceCanonical = sourceEntity?.canonical || {};
  const normalizedStatus =
    relation.status === "verified" || relation.status === "rejected"
      ? relation.status
      : "pending";
  return {
    id: relation.id,
    source_url: asString(sourceCanonical.url),
    source_song_id: relation.from_entity_id,
    source_platform: asString(sourceCanonical.platform),
    target_url: targetResult.url,
    target_song_id: relation.to_entity_id,
    target_platform: targetResult.platform,
    score: relation.match_score ?? 0,
    confidence: relation.confidence ?? 0,
    match_type: relation.relation_data?.manual ? "user" : "system",
    status: normalizedStatus,
    upvotes: relation.upvotes,
    downvotes: relation.downvotes,
    net_votes: relation.net_votes,
    result: targetResult,
    submitted_by_username: relation.discovered_by || undefined,
  };
}

async function discoverEntityByUrl(url: string): Promise<EntityApiResponse> {
  const response = await apiClient.post<DiscoverApiResponse>("/entities/discover", { url, limit: 20 });
  const track = response.data.entities.find((entity) => entity.type === "track");
  if (!track) {
    throw new Error("No track entity found for URL");
  }
  return track;
}

async function getEntityById(entityId: string): Promise<EntityApiResponse> {
  const response = await apiClient.get<EntityApiResponse>(`/entities/${entityId}`);
  return response.data;
}

// API functions
export async function findMatches(
  sourceUrl: string,
  targetPlatforms: string[]
): Promise<FindMatchesResponse> {
  const sourceEntity = await discoverEntityByUrl(sourceUrl);
  const response = await apiClient.post<RelationsApiResponse>(
    `/entities/${sourceEntity.id}/relations:discover`,
    {
      target_providers: targetPlatforms,
      limit: 8,
    } satisfies { target_providers: string[]; limit: number }
  );
  const matches = response.data.relations.map((relation) => relationToMatch(relation, sourceEntity));
  return {
    source_url: sourceUrl,
    matches,
    total: matches.length,
  };
}

export async function getMatch(id: string): Promise<Match> {
  const relationResponse = await apiClient.get<RelationApiResponse>(`/relations/${id}`);
  const sourceEntity = await getEntityById(relationResponse.data.from_entity_id);
  return relationToMatch(relationResponse.data, sourceEntity);
}

export interface SubmitMatchRequest {
  source_url: string;
  target_url: string;
  target_platform: string;
}

export interface MatchPreviewResponse {
  target_url: string;
  target_platform: string;
  result: MatchResult;
}

export async function submitMatch(data: SubmitMatchRequest): Promise<Match> {
  const sourceEntity = await discoverEntityByUrl(data.source_url);
  const relationResponse = await apiClient.post<RelationApiResponse>(
    `/entities/${sourceEntity.id}/relations`,
    {
      to_url: data.target_url,
      relation_type: "audio_match",
      match_score: 85,
    }
  );
  return relationToMatch(relationResponse.data, sourceEntity);
}

export async function previewMatchUrl(targetUrl: string): Promise<MatchPreviewResponse> {
  const discovered = await apiClient.post<DiscoverApiResponse>("/entities/discover", {
    url: targetUrl,
    limit: 3,
  });
  const target = discovered.data.entities.find((entity) => entity.type === "track") ?? discovered.data.entities[0];
  if (!target) {
    throw new Error("Could not preview URL");
  }
  const result = entityToResult(target);
  return {
    target_url: targetUrl,
    target_platform: result.platform,
    result,
  };
}

export async function getMatchesForSong(songId: string): Promise<Match[]> {
  const [sourceEntity, relations] = await Promise.all([
    getEntityById(songId),
    apiClient.get<RelationsApiResponse>(`/entities/${songId}/relations`, {
      params: { relation_type: "audio_match" },
    }),
  ]);
  return relations.data.relations.map((relation) => relationToMatch(relation, sourceEntity));
}

// Query keys
export const matchKeys = {
  all: ["matches"] as const,
  lists: () => [...matchKeys.all, "list"] as const,
  list: (filters: { songId?: string }) => [...matchKeys.lists(), filters] as const,
  details: () => [...matchKeys.all, "detail"] as const,
  detail: (id: string) => [...matchKeys.details(), id] as const,
  find: (sourceUrl: string, platforms: string[]) => [...matchKeys.all, "find", sourceUrl, platforms] as const,
  preview: (targetUrl: string) => [...matchKeys.all, "preview", targetUrl] as const,
};

// Hooks
export function useFindMatches(
  sourceUrl: string,
  targetPlatforms: string[],
  enabled = true
) {
  return useQuery({
    queryKey: matchKeys.find(sourceUrl, targetPlatforms),
    queryFn: () => findMatches(sourceUrl, targetPlatforms),
    enabled: enabled && !!sourceUrl && targetPlatforms.length > 0,
    staleTime: 1000 * 60 * 5,
  });
}

export function useMatch(id: string) {
  return useQuery({
    queryKey: matchKeys.detail(id),
    queryFn: () => getMatch(id),
    enabled: !!id,
  });
}

export function useMatchPreview(targetUrl: string, enabled = true) {
  return useQuery({
    queryKey: matchKeys.preview(targetUrl),
    queryFn: () => previewMatchUrl(targetUrl),
    enabled: enabled && !!targetUrl,
    retry: false,
  });
}

export function useMatchesForSong(songId: string) {
  return useQuery({
    queryKey: matchKeys.list({ songId }),
    queryFn: () => getMatchesForSong(songId),
    enabled: !!songId,
  });
}

export function useFindMatchesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sourceUrl,
      targetPlatforms,
    }: {
      sourceUrl: string;
      targetPlatforms: string[];
    }) => findMatches(sourceUrl, targetPlatforms),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(matchKeys.find(variables.sourceUrl, variables.targetPlatforms), data);
    },
  });
}

export function useSubmitMatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: submitMatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: matchKeys.all });
    },
  });
}

export async function discoverMatchesForEntity(
  entityId: string,
  targetPlatforms?: string[]
): Promise<Match[]> {
  const [sourceEntity, response] = await Promise.all([
    getEntityById(entityId),
    apiClient.post<RelationsApiResponse>(`/entities/${entityId}/relations:discover`, {
      target_providers: targetPlatforms ?? null,
      limit: 8,
    }),
  ]);
  return response.data.relations.map((relation) => relationToMatch(relation, sourceEntity));
}

export function useDiscoverMatchesMutation(songId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetPlatforms?: string[]) =>
      discoverMatchesForEntity(songId, targetPlatforms),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: matchKeys.list({ songId }) });
    },
  });
}
