/**
 * Entity mapping and type coercion utilities.
 *
 * Pure functions that convert raw API response data into typed internal models.
 */

import type {
  EnhancedAlbum,
  EnhancedArtist,
  EnhancedSong,
  InternalPlaylist,
  InternalSong,
  PlatformInfo,
} from "@/types";

// ====== API response interfaces ======

export interface EntityApiResponse {
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

export interface RelationApiResponse {
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

export interface DiscoverApiResponse {
  query: string;
  query_type: "url" | "text";
  entities: EntityApiResponse[];
  total: number;
  entities_created: number;
  top_relations: Record<string, RelationApiResponse[]>;
}

export interface EntitySnapshotsApiResponse {
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

export interface RelationsApiResponse {
  entity_id: string;
  relations: RelationApiResponse[];
  total: number;
}

export interface RefreshApiResponse {
  entity: EntityApiResponse;
  refreshed_snapshots: number;
  failed_providers: Array<{ provider_id: string; error: string }>;
}

// ====== Type coercion helpers ======

export function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

export function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function asNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

export function asBool(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

// ====== Platform builders ======

export function buildPlatformFromCanonical(canonical: Record<string, unknown>): PlatformInfo[] {
  const platform = asString(canonical.platform);
  const platformId = asString(canonical.platform_id);
  const url = asString(canonical.url);
  if (!platform) return [];
  return [{ platform, platform_id: platformId, url }];
}

export function buildPlatformsFromSnapshots(snapshots: EntitySnapshotsApiResponse["snapshots"]): PlatformInfo[] {
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

// ====== Entity converters ======

export function relationTargetToSong(target: EntityApiResponse): InternalSong {
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

export function mapEntityToSearchResult(entity: EntityApiResponse) {
  const canonical = entity.canonical || {};
  const entityType = entity.type as import("@/types").EntityType;
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

/**
 * Pure mapping function: converts pre-fetched entity data into an EnhancedSong.
 */
export function mapEntityDataToSong(
  entity: EntityApiResponse,
  snapshots: EntitySnapshotsApiResponse,
  relations: RelationsApiResponse,
): EnhancedSong {
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

/**
 * Pure mapping function: converts pre-fetched entity data into an EnhancedAlbum.
 */
export function mapEntityDataToAlbum(
  entity: EntityApiResponse,
  snapshots: EntitySnapshotsApiResponse,
  containsRelations: RelationsApiResponse,
): EnhancedAlbum {
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

/**
 * Pure mapping function: converts pre-fetched entity data into an EnhancedArtist.
 */
export function mapEntityDataToArtist(
  entity: EntityApiResponse,
  snapshots: EntitySnapshotsApiResponse,
  performedRelations: RelationsApiResponse,
): EnhancedArtist {
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

/**
 * Pure mapping function: converts pre-fetched entity data into an InternalPlaylist.
 */
export function mapEntityDataToPlaylist(
  entity: EntityApiResponse,
  snapshots: EntitySnapshotsApiResponse,
  containsRelations: RelationsApiResponse,
): InternalPlaylist {
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
