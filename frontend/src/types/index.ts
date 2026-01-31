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

// Entity types
export type EntityType = "artist" | "album" | "playlist" | "track";

export interface Artist {
  id: string;
  name: string;
  platform: string;
  url: string;
  image_url: string | null;
  genres: string[];
  followers: number | null;
  songs: Song[];
  total_songs: number;
}

export interface Album {
  id: string;
  name: string;
  platform: string;
  url: string;
  artist_name: string;
  cover_url: string | null;
  release_date: string | null;
  year: number | null;
  total_tracks: number;
  songs: Song[];
}

export interface Playlist {
  id: string;
  name: string;
  platform: string;
  url: string;
  description: string | null;
  owner_name: string | null;
  cover_url: string | null;
  total_tracks: number;
  songs: Song[];
}

export interface EntitySearchResult {
  entity_type: EntityType;
  id: string;
  name: string;
  platform: string;
  url: string;
  image_url: string | null;
  subtitle: string | null;
}

export interface EntitySearchResponse {
  query: string;
  entity_type: EntityType | null;
  results: EntitySearchResult[];
  total: number;
}
