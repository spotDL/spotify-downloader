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
  id: string;
  platform: string;
  platform_id: string;
  platform_url: string;
  name: string;
  artists: string[];
  album_name: string | null;
  duration_seconds: number;
  isrc: string | null;
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
