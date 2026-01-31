import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { HealthResponse } from "@/types";

// API functions
export async function checkHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>("/health");
  return response.data;
}

// Query keys
export const healthKeys = {
  all: ["health"] as const,
  status: () => [...healthKeys.all, "status"] as const,
};

// Hooks
export function useHealth() {
  return useQuery({
    queryKey: healthKeys.status(),
    queryFn: checkHealth,
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 60, // Refetch every minute
    retry: 1,
  });
}
