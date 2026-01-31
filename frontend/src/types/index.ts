export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  reputation_score: number;
  created_at: string;
}

export interface Song {
  id?: string;
  platform: string;
  platform_id: string;
  url: string;
  name: string;
  artists: string[];
  artist: string;
  album_name: string | null;
  album_id?: string | null;
  duration: number;
  isrc: string | null;
  cover_url?: string | null;
  year?: number | null;
  genres?: string[];
  explicit?: boolean;
  track_number?: number | null;
  disc_number?: number | null;
  date?: string | null;
}

export interface MatchResult {
  name: string;
  artists: string[];
  artist: string;
  duration: number;
  platform: string;
  platform_id: string;
  url: string;
  album_name: string | null;
  cover_url: string | null;
  views: number | null;
  explicit: boolean;
  verified: boolean;
}

export interface Match {
  source_url: string;
  target_url: string;
  target_platform: string;
  score: number;
  confidence: number;
  match_type: string;
  result: MatchResult;
}

export interface Vote {
  id: string;
  match_id: string;
  user_id: string;
  vote_type: "up" | "down";
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface FindMatchesRequest {
  source_url: string;
  target_platforms: string[];
}

export interface FindMatchesResponse {
  source_url: string;
  matches: Match[];
  total: number;
}

// Platform link info (for cross-platform entities)
export interface PlatformInfo {
  platform: string;
  platform_id: string;
  url: string;
  followers?: number | null;
}

// Entity types
export type EntityType = "artist" | "album" | "playlist" | "track" | "all";

// Entity types that can be displayed (excludes "all" filter option)
export type DisplayEntityType = "artist" | "album" | "playlist" | "track";

// Internal ID-based entities
export interface InternalSong {
  id: string; // Internal UUID
  name: string;
  artists: string[];
  artist: string;
  duration: number;
  album_name: string | null;
  cover_url: string | null;
  isrc: string | null;
  year: number | null;
  platforms: PlatformInfo[];
}

export interface AlbumSummary {
  id: string;
  name: string;
  cover_url: string | null;
  year: number | null;
  total_tracks: number;
}

export interface InternalArtist {
  id: string; // Internal UUID
  name: string;
  image_url: string | null;
  genres: string[];
  platforms: PlatformInfo[];
  albums: AlbumSummary[];
  songs: InternalSong[];
  total_albums: number;
  total_songs: number;
}

export interface InternalAlbum {
  id: string; // Internal UUID
  name: string;
  artist_name: string;
  artist_id: string | null;
  cover_url: string | null;
  year: number | null;
  total_tracks: number;
  platforms: PlatformInfo[];
  songs: InternalSong[];
}

export interface InternalPlaylist {
  id: string; // Internal UUID
  name: string;
  owner_name: string | null;
  description: string | null;
  cover_url: string | null;
  total_tracks: number;
  platforms: PlatformInfo[];
  songs: InternalSong[];
}

// Search result with internal ID
export interface SearchResult {
  id: string; // Internal UUID
  entity_type: EntityType;
  name: string;
  subtitle: string | null;
  image_url: string | null;
  platforms: PlatformInfo[];
  duration?: number | null;
}

// Universal search response
export interface UniversalSearchResponse {
  query: string;
  query_type: "url" | "text";
  results: SearchResult[];
  entities_created: number;
  total: number;
}

// Universal search request
export interface UniversalSearchRequest {
  query: string;
  entity_types?: EntityType[];
  limit?: number;
}
