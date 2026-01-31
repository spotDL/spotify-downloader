import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  EntityType,
  InternalArtist,
  InternalAlbum,
  InternalPlaylist,
  InternalSong,
  UniversalSearchResponse,
  UniversalSearchRequest,
} from "@/types";

// API functions for internal ID-based system

export async function getArtistById(id: string): Promise<InternalArtist> {
  const response = await apiClient.get<InternalArtist>(`/entities/artists/${id}`);
  return response.data;
}

export async function getAlbumById(id: string): Promise<InternalAlbum> {
  const response = await apiClient.get<InternalAlbum>(`/entities/albums/${id}`);
  return response.data;
}

export async function getPlaylistById(id: string): Promise<InternalPlaylist> {
  const response = await apiClient.get<InternalPlaylist>(
    `/entities/playlists/${id}`
  );
  return response.data;
}

export async function getSongById(id: string): Promise<InternalSong> {
  const response = await apiClient.get<InternalSong>(`/entities/songs/${id}`);
  return response.data;
}

export async function universalSearch(
  request: UniversalSearchRequest
): Promise<UniversalSearchResponse> {
  const response = await apiClient.post<UniversalSearchResponse>(
    "/search",
    request
  );
  return response.data;
}

export async function universalSearchGet(
  query: string,
  type?: EntityType,
  limit = 20
): Promise<UniversalSearchResponse> {
  const params: Record<string, string | number> = { q: query, limit };
  if (type && type !== "all") {
    params.type = type;
  }
  const response = await apiClient.get<UniversalSearchResponse>("/search", {
    params,
  });
  return response.data;
}

// Query keys

export const entityKeys = {
  all: ["entities"] as const,
  artists: () => [...entityKeys.all, "artists"] as const,
  artist: (id: string) => [...entityKeys.artists(), id] as const,
  albums: () => [...entityKeys.all, "albums"] as const,
  album: (id: string) => [...entityKeys.albums(), id] as const,
  playlists: () => [...entityKeys.all, "playlists"] as const,
  playlist: (id: string) => [...entityKeys.playlists(), id] as const,
  songs: () => [...entityKeys.all, "songs"] as const,
  song: (id: string) => [...entityKeys.songs(), id] as const,
  search: (query: string, type?: EntityType) =>
    [...entityKeys.all, "search", query, type] as const,
};

// Hooks

export function useInternalArtist(id: string) {
  return useQuery({
    queryKey: entityKeys.artist(id),
    queryFn: () => getArtistById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

export function useInternalAlbum(id: string) {
  return useQuery({
    queryKey: entityKeys.album(id),
    queryFn: () => getAlbumById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 10,
  });
}

export function useInternalPlaylist(id: string) {
  return useQuery({
    queryKey: entityKeys.playlist(id),
    queryFn: () => getPlaylistById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5, // 5 minutes (playlists change more often)
  });
}

export function useInternalSong(id: string) {
  return useQuery({
    queryKey: entityKeys.song(id),
    queryFn: () => getSongById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useUniversalSearch(
  query: string,
  type?: EntityType,
  limit = 20
) {
  return useQuery({
    queryKey: entityKeys.search(query, type),
    queryFn: () => universalSearchGet(query, type, limit),
    enabled: query.length > 0,
    staleTime: 1000 * 60 * 5,
  });
}

export function useUniversalSearchMutation() {
  return useMutation({
    mutationFn: (request: UniversalSearchRequest) => universalSearch(request),
  });
}
