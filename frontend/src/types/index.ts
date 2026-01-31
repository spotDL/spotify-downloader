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

export interface Match {
  id: string;
  source_song_id: string | null;
  source_platform: string;
  source_url: string;
  target_platform: string;
  target_url: string;
  match_type: "system" | "user";
  match_score: number | null;
  upvotes: number;
  downvotes: number;
  submitted_by: string | null;
  verified_by: string | null;
  created_at: string;
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
  song: Song;
  matches: Match[];
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
