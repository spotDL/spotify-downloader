import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { ExportableSettings } from "@/stores/settings";

// Provider preference type matching backend
export interface ProviderPreferenceApi {
  id: string;
  enabled: boolean;
}

// API response matches our ExportableSettings but with snake_case
export interface UserSettingsResponse {
  // Download
  audio_format: string;
  audio_quality: string;
  bitrate: string | null;
  output_template: string;
  output_directory: string | null;
  max_concurrent_downloads: number;
  overwrite: string;
  max_filename_length: number;
  restrict: string | null;

  // Metadata
  embed_metadata: boolean;
  embed_lyrics: boolean;
  embed_cover: boolean;
  id3_separator: string;

  // SponsorBlock
  sponsor_block: boolean;

  // LRC / Lyrics files
  generate_lrc: boolean;

  // M3U playlist generation
  m3u: string | null;

  // Archive (deduplication)
  archive: string | null;

  // Content filtering
  skip_explicit: boolean;
  scan_for_songs: boolean;

  // Playlist options
  playlist_numbering: boolean;
  fetch_albums: boolean;

  // Proxy
  proxy: string | null;

  // Custom arguments
  ffmpeg_args: string | null;
  yt_dlp_args: string | null;

  // Credentials
  spotify_client_id: string | null;
  spotify_client_secret: string | null;
  spotify_user_auth: boolean;

  // Server
  api_url: string;
  api_timeout: number;
  offline_mode: boolean;

  // Matching
  name_match_threshold: number;
  artist_match_threshold: number;
  time_match_threshold: number;

  // Advanced
  log_level: string;
  cookie_file: string | null;

  // Appearance settings
  compact_sidebar: boolean;
  enable_animations: boolean;
  reduce_motion: boolean;

  // Provider preferences
  audio_source_preferences: ProviderPreferenceApi[] | null;
  metadata_source_preferences: ProviderPreferenceApi[] | null;
  lyrics_source_preferences: ProviderPreferenceApi[] | null;
}

// Convert API response to store format
export function apiToStoreSettings(api: UserSettingsResponse): Partial<ExportableSettings> {
  return {
    audioFormat: api.audio_format as ExportableSettings["audioFormat"],
    audioQuality: api.audio_quality as ExportableSettings["audioQuality"],
    bitrate: api.bitrate ?? "",
    outputTemplate: api.output_template,
    outputDirectory: api.output_directory ?? "",
    maxConcurrentDownloads: api.max_concurrent_downloads,
    overwrite: api.overwrite as ExportableSettings["overwrite"],
    maxFilenameLength: api.max_filename_length,
    restrict: (api.restrict as ExportableSettings["restrict"]) ?? null,
    embedMetadata: api.embed_metadata,
    embedLyrics: api.embed_lyrics,
    embedCover: api.embed_cover,
    id3Separator: api.id3_separator,
    sponsorBlock: api.sponsor_block,
    generateLrc: api.generate_lrc,
    m3u: api.m3u ?? "",
    archive: api.archive ?? "",
    skipExplicit: api.skip_explicit,
    scanForSongs: api.scan_for_songs,
    playlistNumbering: api.playlist_numbering,
    fetchAlbums: api.fetch_albums,
    proxy: api.proxy ?? "",
    ffmpegArgs: api.ffmpeg_args ?? "",
    ytDlpArgs: api.yt_dlp_args ?? "",
    spotifyClientId: api.spotify_client_id ?? "",
    spotifyClientSecret: api.spotify_client_secret ?? "",
    spotifyUserAuth: api.spotify_user_auth,
    apiUrl: api.api_url,
    apiTimeout: api.api_timeout,
    offlineMode: api.offline_mode,
    nameMatchThreshold: api.name_match_threshold,
    artistMatchThreshold: api.artist_match_threshold,
    timeMatchThreshold: api.time_match_threshold,
    logLevel: api.log_level as ExportableSettings["logLevel"],
    cookieFile: api.cookie_file ?? "",
    compactSidebar: api.compact_sidebar,
    enableAnimations: api.enable_animations,
    reduceMotion: api.reduce_motion,
    ...(api.audio_source_preferences && { audioSourcePreferences: api.audio_source_preferences }),
    ...(api.metadata_source_preferences && { metadataSourcePreferences: api.metadata_source_preferences }),
    ...(api.lyrics_source_preferences && { lyricsSourcePreferences: api.lyrics_source_preferences }),
  };
}

// Convert store format to API request
export function storeToApiSettings(store: ExportableSettings): Partial<UserSettingsResponse> {
  return {
    audio_format: store.audioFormat,
    audio_quality: store.audioQuality,
    bitrate: store.bitrate || null,
    output_template: store.outputTemplate,
    output_directory: store.outputDirectory || null,
    max_concurrent_downloads: store.maxConcurrentDownloads,
    overwrite: store.overwrite,
    max_filename_length: store.maxFilenameLength,
    restrict: store.restrict,
    embed_metadata: store.embedMetadata,
    embed_lyrics: store.embedLyrics,
    embed_cover: store.embedCover,
    id3_separator: store.id3Separator,
    sponsor_block: store.sponsorBlock,
    generate_lrc: store.generateLrc,
    m3u: store.m3u || null,
    archive: store.archive || null,
    skip_explicit: store.skipExplicit,
    scan_for_songs: store.scanForSongs,
    playlist_numbering: store.playlistNumbering,
    fetch_albums: store.fetchAlbums,
    proxy: store.proxy || null,
    ffmpeg_args: store.ffmpegArgs || null,
    yt_dlp_args: store.ytDlpArgs || null,
    spotify_client_id: store.spotifyClientId || null,
    spotify_client_secret: store.spotifyClientSecret || null,
    spotify_user_auth: store.spotifyUserAuth,
    api_url: store.apiUrl,
    api_timeout: store.apiTimeout,
    offline_mode: store.offlineMode,
    name_match_threshold: store.nameMatchThreshold,
    artist_match_threshold: store.artistMatchThreshold,
    time_match_threshold: store.timeMatchThreshold,
    log_level: store.logLevel,
    cookie_file: store.cookieFile || null,
    compact_sidebar: store.compactSidebar,
    enable_animations: store.enableAnimations,
    reduce_motion: store.reduceMotion,
    audio_source_preferences: store.audioSourcePreferences,
    metadata_source_preferences: store.metadataSourcePreferences,
    lyrics_source_preferences: store.lyricsSourcePreferences,
  };
}

// API functions
export async function getUserSettings(): Promise<UserSettingsResponse> {
  const response = await apiClient.get<UserSettingsResponse>("/settings/me");
  return response.data;
}

export async function updateUserSettings(
  settings: Partial<UserSettingsResponse>
): Promise<UserSettingsResponse> {
  const response = await apiClient.put<UserSettingsResponse>("/settings/me", settings);
  return response.data;
}

export async function resetUserSettings(): Promise<UserSettingsResponse> {
  const response = await apiClient.delete<UserSettingsResponse>("/settings/me");
  return response.data;
}

export async function exportUserSettings(): Promise<UserSettingsResponse> {
  const response = await apiClient.post<UserSettingsResponse>("/settings/export");
  return response.data;
}

export async function importUserSettings(
  settings: Partial<UserSettingsResponse>
): Promise<UserSettingsResponse> {
  const response = await apiClient.post<UserSettingsResponse>("/settings/import", settings);
  return response.data;
}

// Query keys
export const settingsKeys = {
  all: ["settings"] as const,
  user: () => [...settingsKeys.all, "user"] as const,
};

// Hooks
export function useUserSettings() {
  return useQuery({
    queryKey: settingsKeys.user(),
    queryFn: getUserSettings,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useUpdateUserSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateUserSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(settingsKeys.user(), data);
    },
  });
}

export function useResetUserSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resetUserSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(settingsKeys.user(), data);
    },
  });
}

export function useExportUserSettings() {
  return useMutation({
    mutationFn: exportUserSettings,
  });
}

export function useImportUserSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importUserSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(settingsKeys.user(), data);
    },
  });
}
