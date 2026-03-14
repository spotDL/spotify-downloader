/**
 * API request/response types for paginated endpoints, admin operations,
 * health checks, and matching.
 *
 * Types here reference entity types via inline `import(".")` to avoid
 * circular import issues with index.ts re-exporting this module.
 */

// ====== HEALTH ======
export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

// ====== MATCHING ======
export interface FindMatchesRequest {
  source_url: string;
  target_platforms: string[];
}

export interface FindMatchesResponse {
  source_url: string;
  matches: import(".").Match[];
  total: number;
}

// ====== ADMIN ======
export interface AdminUserListRequest {
  page?: number;
  per_page?: number;
  search?: string;
  is_admin?: boolean;
  is_active?: boolean;
  sort_by?: "created_at" | "reputation_score" | "username";
  sort_order?: "asc" | "desc";
}

export interface AdminUserListResponse {
  users: import(".").AdminUser[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface AdminMatchListRequest {
  page?: number;
  per_page?: number;
  status?: "pending" | "verified" | "rejected";
  match_type?: "system" | "user" | "metadata";
}

export interface AdminMatchListResponse {
  matches: import(".").AdminMatch[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface AdminReportListRequest {
  page?: number;
  per_page?: number;
  status?: import(".").MetadataReportStatus;
  entity_type?: import(".").MetadataReportEntityType;
}

export interface AdminReportListResponse {
  reports: import(".").MetadataReport[];
  total: number;
  page: number;
  per_page: number;
}

// ====== PAGINATION ======
export interface PaginatedRequest {
  page?: number;
  per_page?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
