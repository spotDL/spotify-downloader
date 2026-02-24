import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { HealthResponse } from "@/types";

export interface DetailedHealthResponse extends HealthResponse {
  database: string;
  cache: string;
  components: Record<string, unknown>;
}

export interface ServiceStatusItem {
  name: string;
  display_name: string;
  state: "connected" | "connecting" | "disconnected" | "error";
  latency: number | null;
  error: string | null;
}

export interface ServiceStatusResponse {
  sources: ServiceStatusItem[];
  targets: ServiceStatusItem[];
  metadata: ServiceStatusItem[];
  capabilities: Record<string, ServiceStatusItem[]>;
  overall_state: "connected" | "degraded" | "partial" | "disconnected";
}

// API functions
export async function checkHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>("/health");
  return response.data;
}

export async function checkDetailedHealth(): Promise<DetailedHealthResponse> {
  const response = await apiClient.get<DetailedHealthResponse>("/health/detailed");
  return response.data;
}

export async function checkServiceHealth(): Promise<ServiceStatusResponse> {
  const response = await apiClient.get<ServiceStatusResponse>("/health/services");
  return response.data;
}

// Query keys
export const healthKeys = {
  all: ["health"] as const,
  status: () => [...healthKeys.all, "status"] as const,
  detailed: () => [...healthKeys.all, "detailed"] as const,
  services: () => [...healthKeys.all, "services"] as const,
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

export function useDetailedHealth() {
  return useQuery({
    queryKey: healthKeys.detailed(),
    queryFn: checkDetailedHealth,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 60,
    retry: 1,
  });
}

export function useServiceHealth() {
  return useQuery({
    queryKey: healthKeys.services(),
    queryFn: checkServiceHealth,
    staleTime: 1000 * 20,
    refetchInterval: 1000 * 60,
    retry: 1,
  });
}
