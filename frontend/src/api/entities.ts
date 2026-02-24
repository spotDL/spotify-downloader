import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  EntityType,
  EnhancedArtist,
  EnhancedAlbum,
  InternalPlaylist,
  EnhancedSong,
  UniversalSearchResponse,
  UniversalSearchRequest,
} from "@/types";

// API functions for internal ID-based system

export async function getArtistById(id: string): Promise<EnhancedArtist> {
  const response = await apiClient.get<EnhancedArtist>(`/entities/artists/${id}`);
  return response.data;
}

export async function getAlbumById(id: string): Promise<EnhancedAlbum> {
  const response = await apiClient.get<EnhancedAlbum>(`/entities/albums/${id}`);
  return response.data;
}

export async function getPlaylistById(id: string): Promise<InternalPlaylist> {
  const response = await apiClient.get<InternalPlaylist>(
    `/entities/playlists/${id}`
  );
  return response.data;
}

export async function getSongById(id: string): Promise<EnhancedSong> {
  const response = await apiClient.get<EnhancedSong>(`/entities/songs/${id}`);
  return response.data;
}

export async function universalSearch(
  request: UniversalSearchRequest
): Promise<UniversalSearchResponse> {
  const response = await apiClient.post<UniversalSearchResponse>(
    "/search",
    request
  );
  return response.data;
}

export async function universalSearchGet(
  query: string,
  type?: EntityType,
  limit = 20
): Promise<UniversalSearchResponse> {
  const params: Record<string, string | number> = { q: query, limit };
  if (type && type !== "all") {
    params.type = type;
  }
  const response = await apiClient.get<UniversalSearchResponse>("/search", {
    params,
  });
  return response.data;
}

// Query keys

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
  search: (query: string, type?: EntityType) =>
    [...entityKeys.all, "search", query, type] as const,
};

// Hooks

export function useInternalArtist(id: string) {
  return useQuery({
    queryKey: entityKeys.artist(id),
    queryFn: () => getArtistById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 10, // 10 minutes
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
    staleTime: 1000 * 60 * 5, // 5 minutes (playlists change more often)
  });
}

export function useInternalSong(id: string) {
  return useQuery({
    queryKey: entityKeys.song(id),
    queryFn: () => getSongById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 60, // 1 hour
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
    staleTime: 1000 * 60 * 5,
  });
}

export function useUniversalSearchMutation() {
  return useMutation({
    mutationFn: (request: UniversalSearchRequest) => universalSearch(request),
  });
}

// Metadata source switching

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

export async function getSongMetadataSources(
  songId: string
): Promise<MetadataSourcesResponse> {
  const response = await apiClient.get<MetadataSourcesResponse>(
    `/entities/songs/${songId}/metadata-sources`
  );
  return response.data;
}

export function useMetadataSources(songId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...entityKeys.song(songId), "metadata-sources"],
    queryFn: () => getSongMetadataSources(songId),
    enabled: options?.enabled ?? !!songId,
    staleTime: 1000 * 60 * 30, // 30 minutes
  });
}

// Refresh metadata endpoints

export interface RefreshResponse {
  success: boolean;
  message: string;
  cooldown_seconds?: number | null;
}

export async function refreshSongMetadata(songId: string): Promise<RefreshResponse> {
  const response = await apiClient.post<RefreshResponse>(
    `/entities/songs/${songId}/refresh`
  );
  return response.data;
}

export async function refreshAlbumMetadata(albumId: string): Promise<RefreshResponse> {
  const response = await apiClient.post<RefreshResponse>(
    `/entities/albums/${albumId}/refresh`
  );
  return response.data;
}

export async function refreshArtistMetadata(artistId: string): Promise<RefreshResponse> {
  const response = await apiClient.post<RefreshResponse>(
    `/entities/artists/${artistId}/refresh`
  );
  return response.data;
}

export async function refreshPlaylistMetadata(playlistId: string): Promise<RefreshResponse> {
  const response = await apiClient.post<RefreshResponse>(
    `/entities/playlists/${playlistId}/refresh`
  );
  return response.data;
}

export function useRefreshSongMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (songId: string) => refreshSongMetadata(songId),
    onSuccess: (_, songId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.song(songId) });
    },
  });
}

export function useRefreshAlbumMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (albumId: string) => refreshAlbumMetadata(albumId),
    onSuccess: (_, albumId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.album(albumId) });
    },
  });
}

export function useRefreshArtistMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (artistId: string) => refreshArtistMetadata(artistId),
    onSuccess: (_, artistId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.artist(artistId) });
    },
  });
}

export function useRefreshPlaylistMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (playlistId: string) => refreshPlaylistMetadata(playlistId),
    onSuccess: (_, playlistId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.playlist(playlistId) });
    },
  });
}

// Enrich metadata endpoints

export interface EnrichResponse {
  success: boolean;
  message: string;
  sources_used: string[];
  fields_updated: string[];
}

export async function enrichSongMetadata(songId: string): Promise<EnrichResponse> {
  const response = await apiClient.post<EnrichResponse>(
    `/entities/songs/${songId}/enrich`
  );
  return response.data;
}

export function useEnrichSongMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (songId: string) => enrichSongMetadata(songId),
    onSuccess: (_, songId) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.song(songId) });
    },
  });
}

// Metadata providers

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
  const response = await apiClient.get<MetadataProvidersResponse>(
    "/entities/metadata-providers"
  );
  return response.data;
}

export function useMetadataProviders() {
  return useQuery({
    queryKey: ["metadata-providers"],
    queryFn: getMetadataProviders,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

// ====== MULTI-SOURCE METADATA ======

import type {
  MetadataSnapshot,
  MetadataSourcesResponse as TypedMetadataSourcesResponse,
  AllLyricsResponse,
  LyricsSource,
  FullEnrichmentResult,
} from "@/types/metadata";

/**
 * Get all metadata snapshots for a song with optional raw responses.
 */
export async function getMetadataSnapshots(
  songId: string,
  includeRaw = false
): Promise<TypedMetadataSourcesResponse> {
  const response = await apiClient.get<{
    song_id: string;
    sources: string[];
    snapshots: Array<{
      id: string;
      source: string;
      snapshot_data: Record<string, unknown>;
      raw_response?: Record<string, unknown>;
      fetched_at: string;
      confidence: number;
    }>;
  }>(`/entities/songs/${songId}/metadata-sources`, {
    params: { include_raw: includeRaw },
  });

  // Transform to frontend types
  return {
    songId: response.data.song_id,
    sources: response.data.sources,
    snapshots: response.data.snapshots.map((s) => ({
      id: s.id,
      source: s.source as MetadataSnapshot["source"],
      fetchedAt: s.fetched_at,
      confidence: s.confidence,
      data: s.snapshot_data,
      rawResponse: s.raw_response,
    })),
  };
}

/**
 * Hook to fetch all metadata snapshots for a song.
 */
export function useMetadataSnapshots(
  songId: string,
  options?: { enabled?: boolean; includeRaw?: boolean }
) {
  return useQuery({
    queryKey: [...entityKeys.song(songId), "metadata-snapshots", options?.includeRaw],
    queryFn: () => getMetadataSnapshots(songId, options?.includeRaw ?? false),
    enabled: options?.enabled ?? !!songId,
    staleTime: 1000 * 60 * 30, // 30 minutes
  });
}

/**
 * Get all lyrics from all sources for a song.
 */
export async function getAllLyrics(songId: string): Promise<AllLyricsResponse> {
  const response = await apiClient.get<{
    song_id: string;
    lyrics: Array<{
      source: string;
      lyrics_text: string;
      lyrics_synced?: string | null;
      quality_score?: number | null;
      is_verified: boolean;
      language?: string | null;
      has_translations?: boolean | null;
    }>;
    total_sources: number;
  }>(`/lyrics/song/${songId}/all`);

  // Transform to frontend types
  return {
    songId: response.data.song_id,
    lyrics: response.data.lyrics.map((l) => ({
      source: l.source as LyricsSource["source"],
      lyricsText: l.lyrics_text,
      lyricsSynced: l.lyrics_synced,
      qualityScore: l.quality_score ?? null,
      isVerified: l.is_verified,
      language: l.language,
      hasTranslations: l.has_translations,
    })),
    totalSources: response.data.total_sources,
  };
}

/**
 * Hook to fetch all lyrics for a song from all sources.
 */
export function useAllLyrics(songId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...entityKeys.song(songId), "all-lyrics"],
    queryFn: () => getAllLyrics(songId),
    enabled: options?.enabled ?? !!songId,
    staleTime: 1000 * 60 * 30, // 30 minutes
  });
}

/**
 * Fetch lyrics from all providers (triggers fetch, not just cache).
 */
export async function fetchAllLyrics(songId: string): Promise<AllLyricsResponse> {
  const response = await apiClient.post<{
    song_id: string;
    lyrics: Array<{
      source: string;
      lyrics_text: string;
      lyrics_synced?: string | null;
      quality_score?: number | null;
      is_verified: boolean;
    }>;
    total_sources: number;
  }>(`/lyrics/song/${songId}/fetch-all`);

  return {
    songId: response.data.song_id,
    lyrics: response.data.lyrics.map((l) => ({
      source: l.source as LyricsSource["source"],
      lyricsText: l.lyrics_text,
      lyricsSynced: l.lyrics_synced,
      qualityScore: l.quality_score ?? null,
      isVerified: l.is_verified,
    })),
    totalSources: response.data.total_sources,
  };
}

/**
 * Trigger full enrichment from ALL sources.
 */
export async function enrichSongFromAllSources(
  songId: string
): Promise<FullEnrichmentResult> {
  const response = await apiClient.post<{
    success: boolean;
    message: string;
    metadata_sources_count: number;
    lyrics_sources_count: number;
    metadata_sources: string[];
  }>(`/entities/songs/${songId}/enrich-all`);

  return {
    success: response.data.success,
    message: response.data.message,
    metadataSourcesCount: response.data.metadata_sources_count,
    lyricsSourcesCount: response.data.lyrics_sources_count,
    metadataSources: response.data.metadata_sources,
  };
}

/**
 * Hook to trigger full enrichment from all sources.
 */
export function useFullEnrichment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (songId: string) => enrichSongFromAllSources(songId),
    onSuccess: (_, songId) => {
      // Invalidate all related queries
      queryClient.invalidateQueries({ queryKey: entityKeys.song(songId) });
      queryClient.invalidateQueries({
        queryKey: [...entityKeys.song(songId), "metadata-snapshots"],
      });
      queryClient.invalidateQueries({
        queryKey: [...entityKeys.song(songId), "all-lyrics"],
      });
    },
  });
}
