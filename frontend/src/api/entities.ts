import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  Artist,
  Album,
  Playlist,
  Song,
  EntityType,
  EntitySearchResponse,
} from "@/types";

// API functions
export async function getArtist(platform: string, id: string): Promise<Artist> {
  const response = await apiClient.get<Artist>(
    `/songs/entities/artist/${platform}/${id}`
  );
  return response.data;
}

export async function getAlbum(platform: string, id: string): Promise<Album> {
  const response = await apiClient.get<Album>(
    `/songs/entities/album/${platform}/${id}`
  );
  return response.data;
}

export async function getPlaylist(
  platform: string,
  id: string
): Promise<Playlist> {
  const response = await apiClient.get<Playlist>(
    `/songs/entities/playlist/${platform}/${id}`
  );
  return response.data;
}

export async function getTrack(platform: string, id: string): Promise<Song> {
  const response = await apiClient.get<Song>(
    `/songs/entities/track/${platform}/${id}`
  );
  return response.data;
}

export async function searchEntities(
  query: string,
  entityType?: EntityType,
  platform = "spotify",
  limit = 20
): Promise<EntitySearchResponse> {
  const params: Record<string, string | number> = { query, platform, limit };
  if (entityType) {
    params.entity_type = entityType;
  }
  const response = await apiClient.get<EntitySearchResponse>(
    "/songs/search/entities",
    { params }
  );
  return response.data;
}

// Query keys
export const entityKeys = {
  all: ["entities"] as const,
  artists: () => [...entityKeys.all, "artist"] as const,
  artist: (platform: string, id: string) =>
    [...entityKeys.artists(), platform, id] as const,
  albums: () => [...entityKeys.all, "album"] as const,
  album: (platform: string, id: string) =>
    [...entityKeys.albums(), platform, id] as const,
  playlists: () => [...entityKeys.all, "playlist"] as const,
  playlist: (platform: string, id: string) =>
    [...entityKeys.playlists(), platform, id] as const,
  tracks: () => [...entityKeys.all, "track"] as const,
  track: (platform: string, id: string) =>
    [...entityKeys.tracks(), platform, id] as const,
  search: (query: string, entityType?: EntityType, platform?: string) =>
    [...entityKeys.all, "search", query, entityType, platform] as const,
};

// Hooks
export function useArtist(platform: string, id: string) {
  return useQuery({
    queryKey: entityKeys.artist(platform, id),
    queryFn: () => getArtist(platform, id),
    enabled: !!platform && !!id,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

export function useAlbum(platform: string, id: string) {
  return useQuery({
    queryKey: entityKeys.album(platform, id),
    queryFn: () => getAlbum(platform, id),
    enabled: !!platform && !!id,
    staleTime: 1000 * 60 * 10,
  });
}

export function usePlaylist(platform: string, id: string) {
  return useQuery({
    queryKey: entityKeys.playlist(platform, id),
    queryFn: () => getPlaylist(platform, id),
    enabled: !!platform && !!id,
    staleTime: 1000 * 60 * 5, // 5 minutes (playlists change more often)
  });
}

export function useTrack(platform: string, id: string) {
  return useQuery({
    queryKey: entityKeys.track(platform, id),
    queryFn: () => getTrack(platform, id),
    enabled: !!platform && !!id,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useEntitySearch(
  query: string,
  entityType?: EntityType,
  platform = "spotify",
  limit = 20
) {
  return useQuery({
    queryKey: entityKeys.search(query, entityType, platform),
    queryFn: () => searchEntities(query, entityType, platform, limit),
    enabled: query.length > 0,
    staleTime: 1000 * 60 * 5,
  });
}

export function useEntitySearchMutation() {
  return useMutation({
    mutationFn: ({
      query,
      entityType,
      platform = "spotify",
      limit = 20,
    }: {
      query: string;
      entityType?: EntityType;
      platform?: string;
      limit?: number;
    }) => searchEntities(query, entityType, platform, limit),
  });
}
