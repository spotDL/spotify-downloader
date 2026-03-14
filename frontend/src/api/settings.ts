import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import { defaultSettings, type SettingsData } from "@/stores/settings";

// Provider preference type matching backend
export interface ProviderPreferenceApi {
  id: string;
  enabled: boolean;
}

// API response matches our SettingsData but with snake_case
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

function snakeToCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

function camelToSnake(s: string): string {
  return s.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

function convertKeys(
  obj: object,
  converter: (key: string) => string
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    result[converter(key)] = value;
  }
  return result;
}

// Convert API response to store format
export function apiToStoreSettings(api: UserSettingsResponse): Partial<SettingsData> {
  const converted = convertKeys(api, snakeToCamel);
  // Handle null -> empty string conversions for string fields
  for (const key of Object.keys(converted)) {
    if (converted[key] === null && typeof defaultSettings[key as keyof SettingsData] === 'string') {
      converted[key] = '';
    }
  }
  return converted as Partial<SettingsData>;
}

// Convert store format to API request
export function storeToApiSettings(store: SettingsData): Partial<UserSettingsResponse> {
  const converted = convertKeys(store, camelToSnake);
  // Handle empty string -> null conversions for nullable API fields
  const nullableFields = ['bitrate', 'output_directory', 'm3u', 'archive', 'proxy', 'ffmpeg_args', 'yt_dlp_args', 'spotify_client_id', 'spotify_client_secret', 'cookie_file', 'restrict'];
  for (const field of nullableFields) {
    if (converted[field] === '') converted[field] = null;
  }
  return converted as Partial<UserSettingsResponse>;
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
