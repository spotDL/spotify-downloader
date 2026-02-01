// Re-export metadata types
export * from "./metadata";

// ====== USER & AUTH ======
export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  reputation_score: number;
  created_at: string;
}

// ====== AUDIO FEATURES ======
export interface AudioFeatures {
  bpm: number | null;
  energy: number | null;
  danceability: number | null;
  valence: number | null;
  key: number | null;
  mode: number | null;
  loudness: number | null;
  speechiness: number | null;
  acousticness: number | null;
  instrumentalness: number | null;
  liveness: number | null;
  time_signature: number | null;
}

// ====== BASIC SONG ======
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

// ====== MATCHING ======
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
  id?: string;
  source_url: string;
  target_url: string;
  source_platform?: string;
  target_platform: string;
  score: number;
  confidence: number;
  match_type: "system" | "user";
  status?: "pending" | "verified" | "rejected";
  result: MatchResult;
  upvotes?: number;
  downvotes?: number;
  net_votes?: number;
  created_at?: string;
  submitted_by_username?: string;
  verified_by_username?: string;
}

export interface Vote {
  id: string;
  match_id: string;
  user_id: string;
  vote_type: "up" | "down";
  created_at: string;
}

// ====== API RESPONSES ======
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

// ====== PLATFORM LINKS ======
export interface PlatformInfo {
  platform: string;
  platform_id: string;
  url: string;
  followers?: number | null;
}

// Platform URL patterns for verification
export const PLATFORM_URL_PATTERNS: Record<string, string> = {
  spotify: "https://open.spotify.com/track/{id}",
  apple_music: "https://music.apple.com/...",
  deezer: "https://www.deezer.com/track/{id}",
  youtube_music: "https://music.youtube.com/watch?v={id}",
  youtube: "https://www.youtube.com/watch?v={id}",
  soundcloud: "https://soundcloud.com/{user}/{track}",
  tidal: "https://tidal.com/track/{id}",
  bandcamp: "https://{artist}.bandcamp.com/track/{slug}",
};

// ====== ENTITY TYPES ======
export type EntityType = "artist" | "album" | "playlist" | "track" | "all";
export type DisplayEntityType = "artist" | "album" | "playlist" | "track";

// ====== INTERNAL ENTITIES ======
export interface InternalSong {
  id: string;
  name: string;
  artists: string[];
  artist: string;
  artist_id: string | null;
  duration: number;
  album_name: string | null;
  album_id: string | null;
  cover_url: string | null;
  isrc: string | null;
  year: number | null;
  platforms: PlatformInfo[];
  matches_count?: number;
  explicit?: boolean;
}

export interface EnhancedSong extends InternalSong {
  audio_features: AudioFeatures | null;
  popularity: number | null;
  explicit: boolean;
  release_date: string | null;
  label: string | null;
  copyright_text: string | null;
  genres: string[];
  matches_count: number;
  track_number: number | null;
  disc_number: number | null;
  // Enrichment tracking
  musicbrainz_id: string | null;
  discogs_id: string | null;
  field_sources: Record<string, string> | null;
  enriched_at: string | null;
}

export interface AlbumSummary {
  id: string;
  name: string;
  cover_url: string | null;
  year: number | null;
  total_tracks: number;
  album_type: "album" | "single" | "ep" | "compilation" | null;
}

export interface InternalArtist {
  id: string;
  name: string;
  image_url: string | null;
  genres: string[];
  platforms: PlatformInfo[];
  albums: AlbumSummary[];
  songs: InternalSong[];
  total_albums: number;
  total_songs: number;
}

export interface EnhancedArtist extends InternalArtist {
  monthly_listeners: number | null;
  popularity: number | null;
  bio: string | null;
  origin_country: string | null;
  origin_city: string | null;
  formed_year: number | null;
  external_urls: Record<string, string>;
  related_artists: ArtistSummary[];
}

export interface ArtistSummary {
  id: string;
  name: string;
  image_url: string | null;
  genres: string[];
}

export interface InternalAlbum {
  id: string;
  name: string;
  artist_name: string;
  artist_id: string | null;
  cover_url: string | null;
  year: number | null;
  total_tracks: number;
  platforms: PlatformInfo[];
  songs: InternalSong[];
}

export interface EnhancedAlbum extends InternalAlbum {
  album_type: "album" | "single" | "ep" | "compilation";
  release_date: string | null;
  label: string | null;
  copyright_text: string | null;
  genres: string[];
  popularity: number | null;
}

export interface InternalPlaylist {
  id: string;
  name: string;
  owner_name: string | null;
  description: string | null;
  cover_url: string | null;
  total_tracks: number;
  platforms: PlatformInfo[];
  songs: InternalSong[];
}

// ====== SEARCH ======
export interface SearchResult {
  id: string;
  entity_type: EntityType;
  name: string;
  subtitle: string | null;
  image_url: string | null;
  platforms: PlatformInfo[];
  duration?: number | null;
}

export interface UniversalSearchResponse {
  query: string;
  query_type: "url" | "text";
  results: SearchResult[];
  entities_created: number;
  total: number;
}

export interface UniversalSearchRequest {
  query: string;
  entity_types?: EntityType[];
  limit?: number;
}

// ====== LYRICS ======
export type LyricsSource = "genius" | "musixmatch" | "azlyrics" | "synced";

export interface Lyrics {
  song_id: string;
  lyrics_text: string;
  lyrics_synced: string | null; // LRC format
  source: LyricsSource;
  fetched_at: string;
}

export interface LyricsLine {
  timestamp: number | null; // milliseconds, null for unsynced
  text: string;
}

export interface ParsedLyrics {
  lines: LyricsLine[];
  isSynced: boolean;
  source: LyricsSource;
}

// ====== METADATA REPORTS ======
export type MetadataReportStatus = "pending" | "reviewed" | "fixed" | "dismissed";
export type MetadataReportEntityType = "song" | "artist" | "album" | "playlist";

export interface MetadataReport {
  id: string;
  entity_type: MetadataReportEntityType;
  entity_id: string;
  reporter_id: string;
  reporter_username?: string;
  field_name: string;
  current_value: string;
  suggested_value: string;
  description: string | null;
  status: MetadataReportStatus;
  reviewed_by: string | null;
  reviewed_by_username?: string;
  reviewed_at: string | null;
  created_at: string;
}

export interface CreateMetadataReportRequest {
  entity_type: MetadataReportEntityType;
  entity_id: string;
  field_name: string;
  current_value: string;
  suggested_value: string;
  description?: string;
}

export interface UpdateMetadataReportRequest {
  status: MetadataReportStatus;
  notes?: string;
}

// ====== METADATA SOURCES ======
export type MetadataSourceName = "spotify" | "musicbrainz" | "discogs" | "deezer" | "apple_music";

export interface MetadataSource {
  field: string;
  source: MetadataSourceName;
  confidence: number; // 0-100
}

// ====== SYSTEM STATS ======
export interface EntityCounts {
  songs: number;
  artists: number;
  albums: number;
  playlists: number;
  matches: number;
  users: number;
}

export interface GrowthStats {
  songs_today: number;
  songs_this_week: number;
  downloads_today: number;
  downloads_this_week: number;
  new_users_today: number;
  new_users_this_week: number;
  matches_today: number;
  matches_this_week: number;
}

export interface SystemStats {
  entities: EntityCounts;
  growth: GrowthStats;
  uptime_seconds: number;
}

// ====== ADMIN ======
export interface AdminUser extends User {
  last_login: string | null;
  matches_submitted: number;
  votes_cast: number;
  reports_submitted: number;
}

export interface AdminUserListRequest {
  page?: number;
  per_page?: number;
  search?: string;
  is_admin?: boolean;
  is_active?: boolean;
  sort_by?: "created_at" | "reputation_score" | "username";
  sort_order?: "asc" | "desc";
}

export interface AdminUserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface AdminMatchListRequest {
  page?: number;
  per_page?: number;
  status?: "pending" | "verified" | "rejected";
  match_type?: "system" | "user";
}

export interface AdminMatchListResponse {
  matches: Match[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface AdminReportListRequest {
  page?: number;
  per_page?: number;
  status?: MetadataReportStatus;
  entity_type?: MetadataReportEntityType;
}

export interface AdminReportListResponse {
  reports: MetadataReport[];
  total: number;
  page: number;
  per_page: number;
}

// ====== DOWNLOAD QUEUE ======
export type DownloadStatus = "pending" | "downloading" | "completed" | "failed" | "cancelled";

export interface DownloadItem {
  id: string;
  song_id: string;
  song_name: string;
  artist: string;
  cover_url: string | null;
  status: DownloadStatus;
  progress: number; // 0-100
  speed: string | null; // e.g., "1.2 MB/s"
  eta: number | null; // seconds remaining
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface DownloadQueueStats {
  pending: number;
  active: number;
  completed: number;
  failed: number;
  total: number;
}

// ====== NAVIGATION ======
export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
  adminOnly?: boolean;
}

// ====== UI COMPONENT PROPS ======
export type CoverArtSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "hero";
export type CoverArtShape = "rounded" | "circle";

export interface CoverArtProps {
  src: string | null;
  alt: string;
  size?: CoverArtSize;
  shape?: CoverArtShape;
  className?: string;
  fallbackIcon?: "artist" | "album" | "playlist" | "track";
  showPlayButton?: boolean;
  onPlay?: () => void;
}

export type ScoreLevel = "high" | "medium" | "low";

export interface MatchScoreGaugeProps {
  score: number; // 0-100
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animated?: boolean;
}

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: "sm" | "md" | "lg" | "xl";
  children: React.ReactNode;
}

// ====== TRENDING & POPULAR ======
export interface TrendingMatch {
  match: Match;
  song: InternalSong;
  vote_count: number;
  recent_votes: number;
}

export interface PopularSong extends InternalSong {
  download_count: number;
  match_count: number;
}

export interface PopularArtist extends ArtistSummary {
  song_count: number;
  total_downloads: number;
}

// ====== API PAGINATION ======
export interface PaginatedRequest {
  page?: number;
  per_page?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// ====== ACTIVITY & HISTORY ======
export interface RecentActivity {
  id: string;
  type: "search" | "download" | "match" | "vote";
  entity_type: EntityType;
  entity_id: string;
  entity_name: string;
  entity_image: string | null;
  timestamp: string;
}

export interface UserContribution {
  matches_submitted: number;
  matches_verified: number;
  votes_cast: number;
  reports_submitted: number;
  reputation_earned: number;
}
