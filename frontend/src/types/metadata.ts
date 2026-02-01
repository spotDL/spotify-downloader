/**
 * Types for multi-source metadata storage and display.
 */

// ====== METADATA SNAPSHOT TYPES ======

export type MetadataProviderSource =
  | "spotify"
  | "musicbrainz"
  | "discogs"
  | "deezer"
  | "youtube_music"
  | "apple_music";

/**
 * Normalized metadata fields extracted from provider responses.
 * These fields are standardized across all providers for quick UI access.
 */
export interface NormalizedMetadata {
  // Core track info
  name?: string;
  artists?: string[];
  album_name?: string;
  album_artist?: string;

  // Identifiers
  isrc?: string;
  upc?: string;
  ean?: string;
  musicbrainz_id?: string;
  discogs_id?: string;

  // Dates & Numbers
  release_date?: string; // ISO format
  year?: number;
  track_number?: number;
  disc_number?: number;
  total_tracks?: number;
  total_discs?: number;
  duration_ms?: number;

  // Classification
  genres?: string[];
  styles?: string[]; // Discogs-specific
  explicit?: boolean;
  instrumental?: boolean;

  // Credits & Labels
  label?: string;
  copyright_text?: string;
  producers?: string[];
  writers?: string[];
  engineers?: string[];

  // Audio characteristics (Spotify)
  bpm?: number;
  key?: number;
  mode?: number;
  energy?: number;
  danceability?: number;
  valence?: number;
  loudness?: number;
  speechiness?: number;
  acousticness?: number;
  instrumentalness?: number;
  liveness?: number;

  // Popularity/Quality
  popularity?: number;
  rating?: number;

  // Media
  cover_url?: string;
  preview_url?: string;

  // Source tracking
  source?: string;
  confidence?: number;
}

/**
 * A metadata snapshot from a single provider.
 */
export interface MetadataSnapshot {
  id: string;
  source: MetadataProviderSource;
  fetchedAt: string;
  confidence: number;

  /** Normalized metadata fields for quick access */
  data: NormalizedMetadata;

  /** Complete raw response from the provider's API (optional, for advanced display) */
  rawResponse?: Record<string, unknown>;
}

/**
 * Response from the metadata-sources API endpoint.
 */
export interface MetadataSourcesResponse {
  songId: string;
  sources: string[];
  snapshots: MetadataSnapshot[];
}

// ====== LYRICS SOURCE TYPES ======

export type LyricsProviderSource =
  | "genius"
  | "musixmatch"
  | "azlyrics"
  | "lrclib"
  | "synced";

/**
 * Lyrics from a single provider.
 */
export interface LyricsSource {
  id?: string;
  source: LyricsProviderSource;
  lyricsText: string;
  lyricsSynced?: string | null; // LRC format
  qualityScore: number | null;
  isVerified: boolean;
  language?: string | null;
  hasTranslations?: boolean | null;
}

/**
 * Response from the all-lyrics API endpoint.
 */
export interface AllLyricsResponse {
  songId: string;
  lyrics: LyricsSource[];
  totalSources: number;
}

// ====== MULTI-SOURCE METADATA ======

/**
 * Combined multi-source metadata for a song.
 */
export interface MultiSourceMetadata {
  songId: string;
  snapshots: MetadataSnapshot[];
  lyrics: LyricsSource[];

  /** Merged data with source tracking for each field */
  mergedData: Record<string, { value: unknown; source: string }>;
}

/**
 * Result of a full enrichment operation.
 */
export interface FullEnrichmentResult {
  success: boolean;
  message: string;
  metadataSourcesCount: number;
  lyricsSourcesCount: number;
  metadataSources: string[];
}

// ====== COMPARISON TYPES ======

/**
 * A row in a metadata comparison table.
 */
export interface ComparisonRow {
  field: string;
  label: string;
  values: Array<{
    source: string;
    value: unknown;
  }>;
}

/**
 * Data structure for the comparison table component.
 */
export interface ComparisonData {
  fields: ComparisonRow[];
  sources: string[];
}

// ====== SOURCE DISPLAY HELPERS ======

export const SOURCE_ICONS: Record<MetadataProviderSource, string> = {
  spotify: "spotify",
  musicbrainz: "musicbrainz",
  discogs: "discogs",
  deezer: "deezer",
  youtube_music: "youtube",
  apple_music: "apple",
};

export const SOURCE_LABELS: Record<MetadataProviderSource, string> = {
  spotify: "Spotify",
  musicbrainz: "MusicBrainz",
  discogs: "Discogs",
  deezer: "Deezer",
  youtube_music: "YouTube Music",
  apple_music: "Apple Music",
};

export const SOURCE_COLORS: Record<MetadataProviderSource, string> = {
  spotify: "text-green-500",
  musicbrainz: "text-yellow-500",
  discogs: "text-orange-500",
  deezer: "text-purple-500",
  youtube_music: "text-red-500",
  apple_music: "text-pink-500",
};

export const LYRICS_SOURCE_LABELS: Record<LyricsProviderSource, string> = {
  genius: "Genius",
  musixmatch: "MusixMatch",
  azlyrics: "AZLyrics",
  lrclib: "LRCLIB",
  synced: "Synced",
};

// ====== UTILITY TYPES ======

/**
 * Fields that can be compared across sources.
 */
export const COMPARABLE_FIELDS: Array<{
  key: keyof NormalizedMetadata;
  label: string;
  category: "basic" | "identifiers" | "audio" | "credits" | "classification";
}> = [
  { key: "name", label: "Track Name", category: "basic" },
  { key: "artists", label: "Artists", category: "basic" },
  { key: "album_name", label: "Album", category: "basic" },
  { key: "release_date", label: "Release Date", category: "basic" },
  { key: "year", label: "Year", category: "basic" },
  { key: "isrc", label: "ISRC", category: "identifiers" },
  { key: "musicbrainz_id", label: "MusicBrainz ID", category: "identifiers" },
  { key: "discogs_id", label: "Discogs ID", category: "identifiers" },
  { key: "genres", label: "Genres", category: "classification" },
  { key: "styles", label: "Styles", category: "classification" },
  { key: "explicit", label: "Explicit", category: "classification" },
  { key: "label", label: "Label", category: "credits" },
  { key: "producers", label: "Producers", category: "credits" },
  { key: "writers", label: "Writers", category: "credits" },
  { key: "bpm", label: "BPM", category: "audio" },
  { key: "key", label: "Key", category: "audio" },
  { key: "energy", label: "Energy", category: "audio" },
  { key: "danceability", label: "Danceability", category: "audio" },
  { key: "valence", label: "Valence", category: "audio" },
  { key: "popularity", label: "Popularity", category: "audio" },
];
