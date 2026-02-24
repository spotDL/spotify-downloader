import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface ProviderInfo {
  id: string;
  name: string;
  icon: string;
  default_enabled: boolean;
}

export interface ProvidersResponse {
  audio_sources: ProviderInfo[];
  metadata_sources: ProviderInfo[];
  lyrics_sources: ProviderInfo[];
}

export interface ProviderPreference {
  id: string;
  enabled: boolean;
}

export interface DefaultPreferencesResponse {
  audio: ProviderPreference[];
  metadata: ProviderPreference[];
  lyrics: ProviderPreference[];
}

export const providerKeys = {
  all: ["providers"] as const,
  list: () => [...providerKeys.all, "list"] as const,
  defaults: () => [...providerKeys.all, "defaults"] as const,
};

/**
 * Get all available providers grouped by category.
 */
export async function getProviders(): Promise<ProvidersResponse> {
  const response = await apiClient.get<ProvidersResponse>("/providers");
  return response.data;
}

/**
 * Get default provider preferences.
 */
export async function getDefaultProviderPreferences(): Promise<DefaultPreferencesResponse> {
  const response = await apiClient.get<DefaultPreferencesResponse>("/providers/defaults");
  return response.data;
}

/**
 * Hook to fetch all providers.
 */
export function useProviders() {
  return useQuery({
    queryKey: providerKeys.list(),
    queryFn: getProviders,
    staleTime: 1000 * 60 * 60, // 1 hour - providers rarely change
  });
}

/**
 * Hook to fetch default provider preferences.
 */
export function useDefaultProviderPreferences() {
  return useQuery({
    queryKey: providerKeys.defaults(),
    queryFn: getDefaultProviderPreferences,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}
