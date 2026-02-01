/**
 * Metadata Reports API hooks and functions.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  MetadataReport,
  MetadataReportEntityType,
  MetadataReportStatus,
  CreateMetadataReportRequest,
} from "@/types";

// Response types
export interface ReportResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  field_name: string;
  current_value: string;
  suggested_value: string;
  description: string | null;
  status: string;
  reporter_id: string;
  reporter_username?: string;
  reviewer_id: string | null;
  reviewed_by_username?: string;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface UpdateReportRequest {
  status: MetadataReportStatus;
}

// Query keys
export const reportKeys = {
  all: ["reports"] as const,
  lists: () => [...reportKeys.all, "list"] as const,
  list: (filters: Record<string, unknown>) =>
    [...reportKeys.lists(), filters] as const,
  myReports: (filters?: Record<string, unknown>) =>
    [...reportKeys.all, "my", filters ?? {}] as const,
  detail: (id: string) => [...reportKeys.all, "detail", id] as const,
};

/**
 * Create a new metadata report.
 */
export async function createReport(
  request: CreateMetadataReportRequest
): Promise<ReportResponse> {
  const response = await apiClient.post<ReportResponse>(
    "/api/v1/reports",
    request
  );
  return response.data;
}

/**
 * Get user's own reports.
 */
export async function getMyReports(
  page: number = 1,
  pageSize: number = 20,
  status?: MetadataReportStatus
): Promise<ReportListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;

  const response = await apiClient.get<ReportListResponse>("/api/v1/reports/me", {
    params,
  });
  return response.data;
}

/**
 * List all reports (admin only).
 */
export async function listReports(
  page: number = 1,
  pageSize: number = 20,
  status?: MetadataReportStatus,
  entityType?: MetadataReportEntityType
): Promise<ReportListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;
  if (entityType) params.entity_type = entityType;

  const response = await apiClient.get<ReportListResponse>("/api/v1/reports", {
    params,
  });
  return response.data;
}

/**
 * Get a single report by ID.
 */
export async function getReport(reportId: string): Promise<ReportResponse> {
  const response = await apiClient.get<ReportResponse>(
    `/api/v1/reports/${reportId}`
  );
  return response.data;
}

/**
 * Update report status (admin only).
 */
export async function updateReport(
  reportId: string,
  request: UpdateReportRequest
): Promise<ReportResponse> {
  const response = await apiClient.patch<ReportResponse>(
    `/api/v1/reports/${reportId}`,
    request
  );
  return response.data;
}

/**
 * Delete a report (admin only).
 */
export async function deleteReport(
  reportId: string
): Promise<{ message: string; id: string }> {
  const response = await apiClient.delete<{ message: string; id: string }>(
    `/api/v1/reports/${reportId}`
  );
  return response.data;
}

// React Query hooks

/**
 * Hook to create a new report.
 */
export function useCreateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportKeys.myReports() });
    },
  });
}

/**
 * Hook to get user's own reports.
 */
export function useMyReports(
  page: number = 1,
  pageSize: number = 20,
  status?: MetadataReportStatus
) {
  return useQuery({
    queryKey: reportKeys.myReports({ page, pageSize, status }),
    queryFn: () => getMyReports(page, pageSize, status),
  });
}

/**
 * Hook to list all reports (admin only).
 */
export function useReportsList(
  page: number = 1,
  pageSize: number = 20,
  status?: MetadataReportStatus,
  entityType?: MetadataReportEntityType
) {
  return useQuery({
    queryKey: reportKeys.list({ page, pageSize, status, entityType }),
    queryFn: () => listReports(page, pageSize, status, entityType),
  });
}

/**
 * Hook to get a single report.
 */
export function useReport(reportId: string | undefined) {
  return useQuery({
    queryKey: reportKeys.detail(reportId ?? ""),
    queryFn: () => getReport(reportId!),
    enabled: !!reportId,
  });
}

/**
 * Hook to update report status (admin only).
 */
export function useUpdateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      reportId,
      request,
    }: {
      reportId: string;
      request: UpdateReportRequest;
    }) => updateReport(reportId, request),
    onSuccess: (data, { reportId }) => {
      queryClient.setQueryData(reportKeys.detail(reportId), data);
      queryClient.invalidateQueries({ queryKey: reportKeys.lists() });
    },
  });
}

/**
 * Hook to delete a report (admin only).
 */
export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteReport,
    onSuccess: (_, reportId) => {
      queryClient.removeQueries({ queryKey: reportKeys.detail(reportId) });
      queryClient.invalidateQueries({ queryKey: reportKeys.lists() });
    },
  });
}

/**
 * Convert API response to MetadataReport type.
 */
export function toMetadataReport(response: ReportResponse): MetadataReport {
  return {
    id: response.id,
    entity_type: response.entity_type as MetadataReportEntityType,
    entity_id: response.entity_id,
    reporter_id: response.reporter_id,
    field_name: response.field_name,
    current_value: response.current_value,
    suggested_value: response.suggested_value,
    description: response.description,
    status: response.status as MetadataReportStatus,
    reviewed_by: response.reviewer_id,
    reviewed_at: response.reviewed_at,
    created_at: response.created_at,
  };
}
