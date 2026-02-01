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
  audio_format: string;
  audio_quality: string;
  output_template: string;
  output_directory: string | null;
  max_concurrent_downloads: number;
  overwrite_existing: boolean;
  embed_metadata: boolean;
  embed_lyrics: boolean;
  embed_cover_art: boolean;
  spotify_client_id: string | null;
  spotify_client_secret: string | null;
  spotify_user_auth: boolean;
  api_url: string;
  api_timeout: number;
  offline_mode: boolean;
  name_match_threshold: number;
  artist_match_threshold: number;
  time_match_threshold: number;
  log_level: string;
  cookie_file: string | null;
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
    outputTemplate: api.output_template,
    outputDirectory: api.output_directory ?? "",
    maxConcurrentDownloads: api.max_concurrent_downloads,
    overwriteExisting: api.overwrite_existing,
    embedMetadata: api.embed_metadata,
    embedLyrics: api.embed_lyrics,
    embedCoverArt: api.embed_cover_art,
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
    // Provider preferences - only include if present from API
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
    output_template: store.outputTemplate,
    output_directory: store.outputDirectory || null,
    max_concurrent_downloads: store.maxConcurrentDownloads,
    overwrite_existing: store.overwriteExisting,
    embed_metadata: store.embedMetadata,
    embed_lyrics: store.embedLyrics,
    embed_cover_art: store.embedCoverArt,
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
    // Provider preferences
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
