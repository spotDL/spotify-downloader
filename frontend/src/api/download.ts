import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import { features } from "@/config";

// Types
export interface StartDownloadRequest {
  url: string;
  title: string;
  artist: string;
  album?: string;
  cover_url?: string;
  duration?: number;
  output_format?: string;
  quality?: string;
  // Metadata embedding options
  embed_metadata?: boolean;
  embed_lyrics?: boolean;
  embed_cover_art?: boolean;
}

export interface StartDownloadResponse {
  download_id: string;
  status: string;
  message: string;
}

export interface DownloadProgress {
  download_id: string;
  status: "pending" | "downloading" | "processing" | "completed" | "failed" | "cancelled";
  progress: number;
  speed: string | null;
  eta: string | null;
  filename: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface DownloadListResponse {
  downloads: DownloadProgress[];
  total: number;
}

/**
 * Throws an error if downloads are not enabled (hosted mode).
 */
function requireDownloadsEnabled(): void {
  if (!features.canDownload) {
    throw new Error("Downloads are disabled in hosted mode. Use a self-hosted instance for download functionality.");
  }
}

// API functions
export async function startDownload(request: StartDownloadRequest): Promise<StartDownloadResponse> {
  requireDownloadsEnabled();
  const response = await apiClient.post<StartDownloadResponse>("/download/start", request);
  return response.data;
}

export async function getDownloadStatus(downloadId: string): Promise<DownloadProgress> {
  requireDownloadsEnabled();
  const response = await apiClient.get<DownloadProgress>(`/download/status/${downloadId}`);
  return response.data;
}

export async function listDownloads(): Promise<DownloadListResponse> {
  requireDownloadsEnabled();
  const response = await apiClient.get<DownloadListResponse>("/download/list");
  return response.data;
}

export async function cancelDownload(downloadId: string): Promise<void> {
  requireDownloadsEnabled();
  await apiClient.post(`/download/cancel/${downloadId}`);
}

export function getDownloadFileUrl(downloadId: string): string {
  requireDownloadsEnabled();
  // Get base URL from apiClient
  const baseUrl = apiClient.defaults.baseURL || "";
  return `${baseUrl}/download/file/${downloadId}`;
}

// Query keys
export const downloadKeys = {
  all: ["downloads"] as const,
  list: () => [...downloadKeys.all, "list"] as const,
  status: (id: string) => [...downloadKeys.all, "status", id] as const,
};

// Hooks
export function useDownloadList() {
  return useQuery({
    queryKey: downloadKeys.list(),
    queryFn: listDownloads,
    refetchInterval: 2000, // Poll every 2 seconds for active downloads
  });
}

export function useDownloadStatus(downloadId: string | null) {
  return useQuery({
    queryKey: downloadKeys.status(downloadId || ""),
    queryFn: () => getDownloadStatus(downloadId!),
    enabled: !!downloadId,
    refetchInterval: (query) => {
      // Poll more frequently while downloading
      const status = query.state.data?.status;
      if (status === "downloading" || status === "processing" || status === "pending") {
        return 1000; // Poll every second during download
      }
      return false; // Stop polling when complete
    },
  });
}

export function useStartDownload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: startDownload,
    onSuccess: () => {
      // Invalidate download list to refresh
      queryClient.invalidateQueries({ queryKey: downloadKeys.list() });
    },
  });
}

export function useCancelDownload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: downloadKeys.all });
    },
  });
}
