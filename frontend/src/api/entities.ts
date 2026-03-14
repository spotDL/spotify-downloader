import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  EnhancedAlbum,
  EnhancedArtist,
  EnhancedSong,
  EntityType,
  InternalPlaylist,
  UniversalSearchRequest,
  UniversalSearchResponse,
} from "@/types";
import type {
  AllLyricsResponse,
  FullEnrichmentResult,
  LyricsSource,
  MetadataSnapshot,
  MetadataSourcesResponse as TypedMetadataSourcesResponse,
} from "@/types/metadata";

// Re-export resolution utilities so existing imports keep working
export { isUuid, resolveEntityId } from "./entity-resolution";

// Re-export API response interfaces for consumers
export type {
  EntityApiResponse,
  RelationApiResponse,
  DiscoverApiResponse,
  EntitySnapshotsApiResponse,
  RelationsApiResponse,
  RefreshApiResponse,
} from "./entity-mappers";

import { resolveEntityId } from "./entity-resolution";
import {
  type EntityApiResponse,
  type EntitySnapshotsApiResponse,
  type RelationsApiResponse,
  type RefreshApiResponse,
  type DiscoverApiResponse,
  mapEntityToSearchResult,
  mapEntityDataToSong,
  mapEntityDataToAlbum,
  mapEntityDataToArtist,
  mapEntityDataToPlaylist,
} from "./entity-mappers";

// ====== Low-level entity fetchers ======

async function getEntity(entityId: string): Promise<EntityApiResponse> {
  const resolvedId = await resolveEntityId(entityId);
  const response = await apiClient.get<EntityApiResponse>(`/entities/${resolvedId}`);
  return response.data;
}

async function getEntitySnapshots(entityId: string): Promise<EntitySnapshotsApiResponse> {
  const resolvedId = await resolveEntityId(entityId);
  const response = await apiClient.get<EntitySnapshotsApiResponse>(`/entities/${resolvedId}/snapshots`);
  return response.data;
}

async function getEntityRelations(entityId: string, relationType = "audio_match"): Promise<RelationsApiResponse> {
  const resolvedId = await resolveEntityId(entityId);
  const response = await apiClient.get<RelationsApiResponse>(`/entities/${resolvedId}/relations`, {
    params: { relation_type: relationType },
  });
  return response.data;
}

// ====== Search ======

export async function universalSearch(
  request: UniversalSearchRequest
): Promise<UniversalSearchResponse> {
  const payload: { query?: string; url?: string; types?: string[]; limit?: number } = {
    limit: request.limit ?? 20,
  };
  const query = request.query.trim();
  if (query.startsWith("http://") || query.startsWith("https://")) {
    payload.url = query;
  } else {
    payload.query = query;
  }
  if (request.entity_types && request.entity_types.length > 0) {
    payload.types = request.entity_types.filter((type) => type !== "all");
  }

  const response = await apiClient.post<DiscoverApiResponse>("/entities/discover", payload);
  return {
    query: response.data.query,
    query_type: response.data.query_type,
    results: response.data.entities.map(mapEntityToSearchResult),
    entities_created: response.data.entities_created,
    total: response.data.total,
  };
}

export async function universalSearchGet(
  query: string,
  type?: EntityType,
  limit = 20
): Promise<UniversalSearchResponse> {
  return universalSearch({
    query,
    entity_types: type && type !== "all" ? [type] : undefined,
    limit,
  });
}

// ====== High-level entity getters (fetch + map) ======

export async function getSongById(id: string): Promise<EnhancedSong> {
  const [entity, snapshots, relations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "audio_match"),
  ]);
  return mapEntityDataToSong(entity, snapshots, relations);
}

export async function getAlbumById(id: string): Promise<EnhancedAlbum> {
  const [entity, snapshots, containsRelations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "contains"),
  ]);
  return mapEntityDataToAlbum(entity, snapshots, containsRelations);
}

export async function getArtistById(id: string): Promise<EnhancedArtist> {
  const [entity, snapshots, performedRelations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "performed"),
  ]);
  return mapEntityDataToArtist(entity, snapshots, performedRelations);
}

export async function getPlaylistById(id: string): Promise<InternalPlaylist> {
  const [entity, snapshots, containsRelations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "contains"),
  ]);
  return mapEntityDataToPlaylist(entity, snapshots, containsRelations);
}

// ====== Query key factory ======

export const entityKeys = {
  all: ["entities"] as const,
  artists: () => [...entityKeys.all, "artists"] as const,
  artist: (id: string) => [...entityKeys.artists(), id] as const,
  albums: () => [...entityKeys.all, "albums"] as const,
  album: (id: string) => [...entityKeys.albums(), id] as const,
  playlists: () => [...entityKeys.all, "playlists"] as const,
  playlist: (id: string) => [...entityKeys.playlists(), id] as const,
  songs: () => [...entityKeys.all, "songs"] as const,
  song: (id: string) => [...entityKeys.songs(), id] as const,
  search: (query: string, type?: EntityType) => [...entityKeys.all, "search", query, type] as const,
};

// ====== Query hooks ======

export function useInternalArtist(id: string) {
  return useQuery({
    queryKey: entityKeys.artist(id),
    queryFn: () => getArtistById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 10,
  });
}

export function useInternalAlbum(id: string) {
  return useQuery({
    queryKey: entityKeys.album(id),
    queryFn: () => getAlbumById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 10,
  });
}

export function useInternalPlaylist(id: string) {
  return useQuery({
    queryKey: entityKeys.playlist(id),
    queryFn: () => getPlaylistById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  });
}

export function useInternalSong(id: string) {
  return useQuery({
    queryKey: entityKeys.song(id),
    queryFn: () => getSongById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 30,
  });
}

export function useUniversalSearch(
  params: { query: string; type?: EntityType; limit?: number },
  options?: { enabled?: boolean }
) {
  const { query, type, limit = 20 } = params;
  return useQuery({
    queryKey: entityKeys.search(query, type),
    queryFn: () => universalSearchGet(query, type, limit),
    enabled: options?.enabled ?? query.length > 0,
    staleTime: 1000 * 60 * 2,
  });
}

export function useUniversalSearchMutation() {
  return useMutation({
    mutationFn: (request: UniversalSearchRequest) => universalSearch(request),
  });
}

// ====== Metadata sources ======

export interface MetadataSnapshotResponse {
  id: string;
  source: string;
  snapshot_data: Record<string, unknown>;
  fetched_at: string;
  confidence: number;
}

export interface MetadataSourcesResponse {
  song_id: string;
  sources: string[];
  snapshots: MetadataSnapshotResponse[];
}

export async function getSongMetadataSources(songId: string): Promise<MetadataSourcesResponse> {
  const resolvedId = await resolveEntityId(songId, "track");
  const response = await apiClient.get<EntitySnapshotsApiResponse>(`/entities/${resolvedId}/snapshots`);
  const sources = response.data.snapshots.map((snapshot) => snapshot.provider_id);
  return {
    song_id: songId,
    sources,
    snapshots: response.data.snapshots.map((snapshot) => ({
      id: snapshot.id,
      source: snapshot.provider_id,
      snapshot_data: snapshot.normalized_payload,
      fetched_at: snapshot.fetched_at,
      confidence: snapshot.confidence,
    })),
  };
}

export function useMetadataSources(songId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...entityKeys.song(songId), "metadata-sources"],
    queryFn: () => getSongMetadataSources(songId),
    enabled: options?.enabled ?? !!songId,
    staleTime: 1000 * 60 * 15,
  });
}

// ====== Refresh / Enrich ======

export interface RefreshResponse {
  success: boolean;
  message: string;
  cooldown_seconds?: number | null;
}

async function refreshEntityMetadata(entityId: string): Promise<RefreshApiResponse> {
  const resolvedId = await resolveEntityId(entityId);
  const response = await apiClient.post<RefreshApiResponse>(`/entities/${resolvedId}/refresh`, {});
  return response.data;
}

export async function refreshSongMetadata(songId: string): Promise<RefreshResponse> {
  const response = await refreshEntityMetadata(songId);
  return {
    success: true,
    message: `Refreshed ${response.refreshed_snapshots} snapshot(s)`,
    cooldown_seconds: null,
  };
}

export async function refreshAlbumMetadata(albumId: string): Promise<RefreshResponse> {
  return refreshSongMetadata(albumId);
}

export async function refreshArtistMetadata(artistId: string): Promise<RefreshResponse> {
  return refreshSongMetadata(artistId);
}

export async function refreshPlaylistMetadata(playlistId: string): Promise<RefreshResponse> {
  return refreshSongMetadata(playlistId);
}

function useRefreshMutation(keyBuilder: (id: string) => readonly unknown[]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => refreshSongMetadata(id),
    onSuccess: (_result, id) => {
      queryClient.invalidateQueries({ queryKey: keyBuilder(id) });
    },
  });
}

export function useRefreshSongMetadata() {
  return useRefreshMutation(entityKeys.song);
}

export function useRefreshAlbumMetadata() {
  return useRefreshMutation(entityKeys.album);
}

export function useRefreshArtistMetadata() {
  return useRefreshMutation(entityKeys.artist);
}

export function useRefreshPlaylistMetadata() {
  return useRefreshMutation(entityKeys.playlist);
}

export interface EnrichResponse {
  success: boolean;
  message: string;
  sources_used: string[];
  fields_updated: string[];
}

export async function enrichSongMetadata(songId: string): Promise<EnrichResponse> {
  const refreshed = await refreshEntityMetadata(songId);
  return {
    success: true,
    message: `Refreshed ${refreshed.refreshed_snapshots} snapshot(s)`,
    sources_used: refreshed.entity.capabilities ? Object.keys(refreshed.entity.capabilities) : [],
    fields_updated: [],
  };
}

export function useEnrichSongMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (songId: string) => enrichSongMetadata(songId),
    onSuccess: (_result, songId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.song(songId) });
    },
  });
}

// ====== Metadata providers ======

export interface MetadataProvider {
  id: string;
  name: string;
  description: string;
  icon: string;
  features: string[];
  rate_limit: string;
  auth_required: boolean;
}

export interface MetadataProvidersResponse {
  providers: MetadataProvider[];
}

export async function getMetadataProviders(): Promise<MetadataProvidersResponse> {
  const response = await apiClient.get<{
    providers: Array<{
      provider_id: string;
      display_name: string;
      capabilities: string[];
      status: string;
    }>;
  }>("/providers/capabilities");
  return {
    providers: response.data.providers.map((provider) => ({
      id: provider.provider_id,
      name: provider.display_name,
      description: `Status: ${provider.status}`,
      icon: provider.provider_id,
      features: provider.capabilities,
      rate_limit: "n/a",
      auth_required: false,
    })),
  };
}

export function useMetadataProviders() {
  return useQuery({
    queryKey: ["metadata-providers"],
    queryFn: getMetadataProviders,
    staleTime: 1000 * 60 * 30,
  });
}

// ====== Metadata snapshots ======

export async function getMetadataSnapshots(
  songId: string,
  _includeRaw = false
): Promise<TypedMetadataSourcesResponse> {
  const resolvedId = await resolveEntityId(songId, "track");
  const response = await apiClient.get<EntitySnapshotsApiResponse>(`/entities/${resolvedId}/snapshots`);
  return {
    songId: songId,
    sources: response.data.snapshots.map((snapshot) => snapshot.provider_id),
    snapshots: response.data.snapshots.map((snapshot) => ({
      id: snapshot.id,
      source: snapshot.provider_id as MetadataSnapshot["source"],
      fetchedAt: snapshot.fetched_at,
      confidence: snapshot.confidence,
      data: snapshot.normalized_payload,
      rawResponse: snapshot.raw_payload,
    })),
  };
}

export function useMetadataSnapshots(
  songId: string,
  options?: { enabled?: boolean; includeRaw?: boolean }
) {
  return useQuery({
    queryKey: [...entityKeys.song(songId), "metadata-snapshots", options?.includeRaw],
    queryFn: () => getMetadataSnapshots(songId, options?.includeRaw ?? false),
    enabled: options?.enabled ?? !!songId,
    staleTime: 1000 * 60 * 10,
  });
}

// ====== Lyrics ======

export async function getAllLyrics(songId: string): Promise<AllLyricsResponse> {
  try {
    const resolvedId = await resolveEntityId(songId, "track");
    const response = await apiClient.get<{
      entity_id: string;
      lyrics: Array<{
        source: string;
        lyrics_text: string;
        lyrics_synced: string | null;
        quality_score: number | null;
        is_verified: boolean;
        language: string | null;
        has_translations: boolean | null;
      }>;
      total_sources: number;
    }>(`/lyrics/entity/${resolvedId}/all`);
    return {
      songId,
      lyrics: response.data.lyrics.map((l) => ({
        source: l.source as LyricsSource["source"],
        lyricsText: l.lyrics_text,
        lyricsSynced: l.lyrics_synced,
        qualityScore: l.quality_score,
        isVerified: l.is_verified,
        language: l.language,
        hasTranslations: l.has_translations,
      })),
      totalSources: response.data.total_sources,
    };
  } catch {
    return {
      songId,
      lyrics: [],
      totalSources: 0,
    };
  }
}

export function useAllLyrics(songId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...entityKeys.song(songId), "all-lyrics"],
    queryFn: () => getAllLyrics(songId),
    enabled: options?.enabled ?? !!songId,
    staleTime: 1000 * 60 * 10,
  });
}

export async function fetchAllLyrics(songId: string): Promise<AllLyricsResponse> {
  try {
    const resolvedId = await resolveEntityId(songId, "track");
    const response = await apiClient.post<{
      entity_id: string;
      lyrics: Array<{
        source: string;
        lyrics_text: string;
        lyrics_synced: string | null;
        quality_score: number | null;
        is_verified: boolean;
        language?: string | null;
        has_translations?: boolean | null;
      }>;
      total_sources: number;
    }>(`/lyrics/entity/${resolvedId}/fetch-all`);
    return {
      songId,
      lyrics: response.data.lyrics.map((l) => ({
        source: l.source as LyricsSource["source"],
        lyricsText: l.lyrics_text,
        lyricsSynced: l.lyrics_synced,
        qualityScore: l.quality_score,
        isVerified: l.is_verified,
        language: l.language ?? null,
        hasTranslations: l.has_translations ?? null,
      })),
      totalSources: response.data.total_sources,
    };
  } catch {
    return {
      songId,
      lyrics: [],
      totalSources: 0,
    };
  }
}

// ====== Full enrichment ======

export async function enrichSongFromAllSources(songId: string): Promise<FullEnrichmentResult> {
  await refreshEntityMetadata(songId);
  return {
    success: true,
    message: "Entity refreshed from all available providers",
    metadataSourcesCount: 0,
    lyricsSourcesCount: 0,
    metadataSources: [],
  };
}

export function useFullEnrichment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (songId: string) => enrichSongFromAllSources(songId),
    onSuccess: (_result, songId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.song(songId) });
      queryClient.invalidateQueries({ queryKey: [...entityKeys.song(songId), "metadata-snapshots"] });
      queryClient.invalidateQueries({ queryKey: [...entityKeys.song(songId), "all-lyrics"] });
    },
  });
}

// ====== Submit lyrics ======

export async function submitLyrics(
  songId: string,
  params: {
    source: string;
    lyricsText: string;
    lyricsSynced?: null | string;
  }
): Promise<LyricsSource> {
  const resolvedId = await resolveEntityId(songId, "track");
  const response = await apiClient.post<any>(`/lyrics/entity/${resolvedId}`, {
    source: params.source,
    lyrics_text: params.lyricsText,
    lyrics_synced: params.lyricsSynced,
  });
  return {
    source: response.data.source as LyricsSource["source"],
    lyricsText: response.data.lyrics_text,
    lyricsSynced: response.data.lyrics_synced,
    qualityScore: response.data.quality_score,
    isVerified: response.data.is_verified,
    language: response.data.language ?? null,
    hasTranslations: response.data.has_translations ?? null,
  };
}

export function useSubmitLyrics() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      songId: string;
      source: string;
      lyricsText: string;
      lyricsSynced?: null | string;
    }) => submitLyrics(data.songId, {
      source: data.source,
      lyricsText: data.lyricsText,
      lyricsSynced: data.lyricsSynced,
    }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [...entityKeys.song(variables.songId), "all-lyrics"] });
    },
  });
}
