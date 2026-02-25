import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  EnhancedAlbum,
  EnhancedArtist,
  EnhancedSong,
  EntityType,
  InternalPlaylist,
  InternalSong,
  PlatformInfo,
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

interface EntityApiResponse {
  id: string;
  type: "track" | "album" | "artist" | "playlist";
  name: string;
  canonical: Record<string, unknown>;
  capabilities: Record<string, unknown>;
  quality_score: number;
  last_merged_at: string;
  merge_version: number;
  refs: {
    album_entity_id: string | null;
    artist_entity_id: string | null;
  };
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

interface DiscoverApiResponse {
  query: string;
  query_type: "url" | "text";
  entities: EntityApiResponse[];
  total: number;
  entities_created: number;
  top_relations: Record<string, RelationApiResponse[]>;
}

type DiscoverEntityType = EntityApiResponse["type"];
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const entityIdResolutionCache = new Map<string, string>();

interface EntitySnapshotsApiResponse {
  entity_id: string;
  snapshots: Array<{
    id: string;
    provider_id: string;
    provider_entity_id: string | null;
    provider_url: string | null;
    normalized_payload: Record<string, unknown>;
    raw_payload: Record<string, unknown>;
    confidence: number;
    fetched_at: string;
    expires_at: string | null;
    capabilities: Record<string, unknown>;
  }>;
  provenance: Array<{
    id: string;
    field_name: string;
    snapshot_id: string;
    score: number;
    selected: boolean;
    reason: string | null;
  }>;
}

interface RelationsApiResponse {
  entity_id: string;
  relations: RelationApiResponse[];
  total: number;
}

interface RefreshApiResponse {
  entity: EntityApiResponse;
  refreshed_snapshots: number;
  failed_providers: Array<{ provider_id: string; error: string }>;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function asBool(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

export function isUuid(value: string): boolean {
  return UUID_REGEX.test(value);
}

function buildCandidateUrls(entityId: string, expectedType?: DiscoverEntityType): string[] {
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

function pickDiscoveredEntity(
  entities: EntityApiResponse[],
  expectedType?: DiscoverEntityType
): EntityApiResponse | null {
  if (!entities.length) return null;
  if (expectedType) {
    return entities.find((entity) => entity.type === expectedType) ?? null;
  }
  return entities[0];
}

async function discoverEntity(
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

function buildPlatformFromCanonical(canonical: Record<string, unknown>): PlatformInfo[] {
  const platform = asString(canonical.platform);
  const platformId = asString(canonical.platform_id);
  const url = asString(canonical.url);
  if (!platform) return [];
  return [{ platform, platform_id: platformId, url }];
}

function buildPlatformsFromSnapshots(snapshots: EntitySnapshotsApiResponse["snapshots"]): PlatformInfo[] {
  const seen = new Set<string>();
  const platforms: PlatformInfo[] = [];
  for (const snapshot of snapshots) {
    const key = `${snapshot.provider_id}:${snapshot.provider_entity_id || snapshot.provider_url || ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    platforms.push({
      platform: snapshot.provider_id,
      platform_id: snapshot.provider_entity_id || "",
      url: snapshot.provider_url || asString(snapshot.normalized_payload.url),
    });
  }
  return platforms;
}

function relationTargetToSong(target: EntityApiResponse): InternalSong {
  const canonical = target.canonical || {};
  const refs = target.refs ?? {};
  return {
    id: target.id,
    name: target.name,
    artists: asStringArray(canonical.artists).length > 0 ? asStringArray(canonical.artists) : [asString(canonical.artist, "Unknown")],
    artist: asString(canonical.artist, "Unknown"),
    artist_id: refs.artist_entity_id ?? null,
    duration: asNumber(canonical.duration, 0),
    album_name: asString(canonical.album_name) || null,
    album_id: refs.album_entity_id ?? null,
    cover_url: asString(canonical.cover_url) || null,
    isrc: asString(canonical.isrc) || null,
    year: asNullableNumber(canonical.year),
    platforms: buildPlatformFromCanonical(canonical),
    matches_count: 0,
    explicit: asBool(canonical.explicit, false),
  };
}

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

function mapEntityToSearchResult(entity: EntityApiResponse) {
  const canonical = entity.canonical || {};
  const entityType = entity.type as EntityType;
  let subtitle: string | null = null;
  if (entityType === "track") {
    subtitle = asString(canonical.artist) || asStringArray(canonical.artists).join(", ") || null;
  } else if (entityType === "album") {
    subtitle = asString(canonical.artist) || null;
  } else if (entityType === "artist") {
    subtitle = "Artist";
  } else if (entityType === "playlist") {
    subtitle = asString(canonical.owner) || "Playlist";
  }

  return {
    id: entity.id,
    entity_type: entityType,
    name: entity.name,
    subtitle,
    image_url: asString(canonical.cover_url) || null,
    platforms: buildPlatformFromCanonical(canonical),
    duration: asNullableNumber(canonical.duration),
  };
}

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

async function mapSongFromEntity(entityId: string): Promise<EnhancedSong> {
  const [entity, snapshots, relations] = await Promise.all([
    getEntity(entityId),
    getEntitySnapshots(entityId),
    getEntityRelations(entityId, "audio_match"),
  ]);

  const canonical = entity.canonical || {};
  const platforms = buildPlatformsFromSnapshots(snapshots.snapshots);
  const artists = asStringArray(canonical.artists);
  const primaryArtist = asString(canonical.artist, artists[0] || "Unknown");

  return {
    id: entity.id,
    name: entity.name,
    artists: artists.length > 0 ? artists : [primaryArtist],
    artist: primaryArtist,
    artist_id: entity.refs?.artist_entity_id ?? null,
    duration: asNumber(canonical.duration, 0),
    album_name: asString(canonical.album_name) || null,
    album_id: entity.refs?.album_entity_id ?? null,
    cover_url: asString(canonical.cover_url) || null,
    isrc: asString(canonical.isrc) || null,
    year: asNullableNumber(canonical.year),
    platforms: platforms.length > 0 ? platforms : buildPlatformFromCanonical(canonical),
    matches_count: relations.total,
    audio_features: {
      bpm: asNullableNumber(canonical.bpm),
      energy: asNullableNumber(canonical.energy),
      danceability: asNullableNumber(canonical.danceability),
      valence: asNullableNumber(canonical.valence),
      key: asNullableNumber(canonical.key),
      mode: asNullableNumber(canonical.mode),
      loudness: asNullableNumber(canonical.loudness),
      speechiness: asNullableNumber(canonical.speechiness),
      acousticness: asNullableNumber(canonical.acousticness),
      instrumentalness: asNullableNumber(canonical.instrumentalness),
      liveness: asNullableNumber(canonical.liveness),
      time_signature: asNullableNumber(canonical.time_signature),
    },
    popularity: asNullableNumber(canonical.popularity),
    explicit: asBool(canonical.explicit, false),
    release_date: asString(canonical.date) || null,
    label: asString(canonical.label) || null,
    copyright_text: asString(canonical.copyright_text) || null,
    genres: asStringArray(canonical.genres),
    track_number: asNullableNumber(canonical.track_number),
    disc_number: asNullableNumber(canonical.disc_number),
    musicbrainz_id: asString(canonical.musicbrainz_id) || null,
    discogs_id: asString(canonical.discogs_id) || null,
    field_sources: null,
    enriched_at: entity.last_merged_at,
  };
}

export async function getSongById(id: string): Promise<EnhancedSong> {
  return mapSongFromEntity(id);
}

export async function getAlbumById(id: string): Promise<EnhancedAlbum> {
  const [entity, snapshots, containsRelations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "contains"),
  ]);

  const canonical = entity.canonical || {};
  const seenAlbum = new Set<string>();
  const songs = containsRelations.relations
    .map((relation) => relation.target)
    .filter((target): target is EntityApiResponse => {
      if (!target) return false;
      if (seenAlbum.has(target.id)) return false;
      seenAlbum.add(target.id);
      return true;
    })
    .map(relationTargetToSong);

  return {
    id: entity.id,
    name: entity.name,
    artist_name: asString(canonical.artist, "Unknown Artist"),
    artist_id: entity.refs?.artist_entity_id ?? null,
    cover_url: asString(canonical.cover_url) || null,
    year: asNullableNumber(canonical.year),
    total_tracks: songs.length > 0 ? songs.length : asNumber(canonical.track_count, 0),
    platforms: buildPlatformsFromSnapshots(snapshots.snapshots),
    songs,
    album_type: (asString(canonical.album_type) || "album") as EnhancedAlbum["album_type"],
    release_date: asString(canonical.date) || null,
    label: asString(canonical.label) || null,
    copyright_text: asString(canonical.copyright_text) || null,
    genres: asStringArray(canonical.genres),
    popularity: asNullableNumber(canonical.popularity),
  };
}

export async function getArtistById(id: string): Promise<EnhancedArtist> {
  const [entity, snapshots, performedRelations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "performed"),
  ]);

  const canonical = entity.canonical || {};
  const seenArtist = new Set<string>();
  const songs = performedRelations.relations
    .map((relation) => relation.target)
    .filter((target): target is EntityApiResponse => {
      if (!target) return false;
      if (seenArtist.has(target.id)) return false;
      seenArtist.add(target.id);
      return true;
    })
    .map(relationTargetToSong);

  const albumMap = new Map<string, { id: string | null; name: string; cover_url: string | null; year: number | null; total_tracks: number; album_type: "album" | "single" | "ep" | "compilation" | null }>();
  for (const song of songs) {
    const key = song.album_id ?? song.album_name ?? `${song.artist}-${song.name}`;
    const existing = albumMap.get(key);
    if (!existing) {
      albumMap.set(key, {
        id: song.album_id ?? null,
        name: song.album_name || "Unknown Album",
        cover_url: song.cover_url || null,
        year: song.year ?? null,
        total_tracks: 1,
        album_type: "album",
      });
    } else {
      existing.total_tracks += 1;
    }
  }

  return {
    id: entity.id,
    name: entity.name,
    image_url: asString(canonical.cover_url) || null,
    genres: asStringArray(canonical.genres),
    platforms: buildPlatformsFromSnapshots(snapshots.snapshots),
    albums: Array.from(albumMap.values()),
    songs,
    total_albums: albumMap.size,
    total_songs: songs.length,
    monthly_listeners: asNullableNumber(canonical.monthly_listeners),
    popularity: asNullableNumber(canonical.popularity),
    bio: asString(canonical.bio) || null,
    origin_country: asString(canonical.origin_country) || null,
    origin_city: asString(canonical.origin_city) || null,
    formed_year: asNullableNumber(canonical.formed_year),
    external_urls: {},
    related_artists: [],
  };
}

export async function getPlaylistById(id: string): Promise<InternalPlaylist> {
  const [entity, snapshots, containsRelations] = await Promise.all([
    getEntity(id),
    getEntitySnapshots(id),
    getEntityRelations(id, "contains"),
  ]);

  const canonical = entity.canonical || {};
  const seenPlaylist = new Set<string>();
  const songs = containsRelations.relations
    .map((relation) => relation.target)
    .filter((target): target is EntityApiResponse => {
      if (!target) return false;
      if (seenPlaylist.has(target.id)) return false;
      seenPlaylist.add(target.id);
      return true;
    })
    .map(relationTargetToSong);

  return {
    id: entity.id,
    name: entity.name,
    owner_name: asString(canonical.owner) || asString(canonical.artist) || null,
    description: asString(canonical.description) || null,
    cover_url: asString(canonical.cover_url) || null,
    total_tracks: songs.length > 0 ? songs.length : asNumber(canonical.track_count, 0),
    platforms: buildPlatformsFromSnapshots(snapshots.snapshots),
    songs,
  };
}

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

function createRefreshMutation(keyBuilder: (id: string) => readonly unknown[]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => refreshSongMetadata(id),
    onSuccess: (_result, id) => {
      queryClient.invalidateQueries({ queryKey: keyBuilder(id) });
    },
  });
}

export function useRefreshSongMetadata() {
  return createRefreshMutation(entityKeys.song);
}

export function useRefreshAlbumMetadata() {
  return createRefreshMutation(entityKeys.album);
}

export function useRefreshArtistMetadata() {
  return createRefreshMutation(entityKeys.artist);
}

export function useRefreshPlaylistMetadata() {
  return createRefreshMutation(entityKeys.playlist);
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

export async function getAllLyrics(songId: string): Promise<AllLyricsResponse> {
  try {
    const resolvedId = await resolveEntityId(songId, "track");
    const response = await apiClient.get<{
      song_id: string;
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
    }>(`/lyrics/song/${resolvedId}/all`);
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
      song_id: string;
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
    }>(`/lyrics/song/${resolvedId}/fetch-all`);
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

export async function submitLyrics(
  songId: string,
  params: {
    source: string;
    lyricsText: string;
    lyricsSynced?: null | string;
  }
): Promise<LyricsSource> {
  const resolvedId = await resolveEntityId(songId, "track");
  const response = await apiClient.post<any>(`/lyrics/song/${resolvedId}`, {
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
