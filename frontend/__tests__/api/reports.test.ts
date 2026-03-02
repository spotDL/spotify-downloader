import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import {
  createReport,
  getMyReports,
  listReports,
  getReport,
  updateReport,
  deleteReport,
  useCreateReport,
  useMyReports,
  useReportsList,
  useReport,
  useUpdateReport,
  useDeleteReport,
  toMetadataReport,
  reportKeys,
  type ReportResponse,
  type ReportListResponse,
} from "../../src/api/reports";
import { apiClient } from "../../src/api/client";
import type { CreateMetadataReportRequest, MetadataReportStatus } from "../../src/types";

type ReportStatus = MetadataReportStatus;

// Mock the API client
vi.mock("../../src/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApiClient = vi.mocked(apiClient);

// Create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("Reports API", () => {
  const mockReportResponse: ReportResponse = {
    id: "report-123",
    entity_type: "song",
    entity_id: "song-456",
    field_name: "name",
    current_value: "Wrong Name",
    suggested_value: "Correct Name",
    description: "The song name is incorrect",
    status: "pending",
    reporter_id: "user-789",
    reviewer_id: null,
    reviewed_at: null,
    created_at: "2024-12-01T00:00:00Z",
    updated_at: "2024-12-01T00:00:00Z",
  };

  const mockReportListResponse: ReportListResponse = {
    reports: [mockReportResponse],
    total: 1,
    page: 1,
    page_size: 20,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("reportKeys", () => {
    it("should generate correct all key", () => {
      expect(reportKeys.all).toEqual(["reports"]);
    });

    it("should generate correct lists key", () => {
      expect(reportKeys.lists()).toEqual(["reports", "list"]);
    });

    it("should generate correct list key with filters", () => {
      const filters = { page: 1, pageSize: 20, status: "pending" };
      expect(reportKeys.list(filters)).toEqual(["reports", "list", filters]);
    });

    it("should generate correct myReports key", () => {
      expect(reportKeys.myReports()).toEqual(["reports", "my", {}]);
    });

    it("should generate correct myReports key with filters", () => {
      const filters = { page: 1, status: "reviewed" };
      expect(reportKeys.myReports(filters)).toEqual(["reports", "my", filters]);
    });

    it("should generate correct detail key", () => {
      expect(reportKeys.detail("report-123")).toEqual([
        "reports",
        "detail",
        "report-123",
      ]);
    });
  });

  describe("createReport", () => {
    const createRequest: CreateMetadataReportRequest = {
      entity_type: "song",
      entity_id: "song-456",
      field_name: "name",
      current_value: "Wrong Name",
      suggested_value: "Correct Name",
      description: "The song name is incorrect",
    };

    it("should create a new report", async () => {
      mockApiClient.post.mockResolvedValueOnce({ data: mockReportResponse });

      const result = await createReport(createRequest);

      expect(mockApiClient.post).toHaveBeenCalledWith(
        "/reports",
        createRequest
      );
      expect(result).toEqual(mockReportResponse);
    });

    it("should throw error on API failure", async () => {
      mockApiClient.post.mockRejectedValueOnce(new Error("Creation failed"));

      await expect(createReport(createRequest)).rejects.toThrow(
        "Creation failed"
      );
    });
  });

  describe("getMyReports", () => {
    it("should fetch user reports with default params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      const result = await getMyReports();

      expect(mockApiClient.get).toHaveBeenCalledWith("/reports/me", {
        params: { page: 1, page_size: 20 },
      });
      expect(result).toEqual(mockReportListResponse);
    });

    it("should fetch user reports with custom params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      await getMyReports(2, 10, "reviewed");

      expect(mockApiClient.get).toHaveBeenCalledWith("/reports/me", {
        params: { page: 2, page_size: 10, status: "reviewed" },
      });
    });

    it("should throw error on API failure", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      await expect(getMyReports()).rejects.toThrow("Fetch failed");
    });
  });

  describe("listReports", () => {
    it("should list all reports with default params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      const result = await listReports();

      expect(mockApiClient.get).toHaveBeenCalledWith("/reports", {
        params: { page: 1, page_size: 20 },
      });
      expect(result).toEqual(mockReportListResponse);
    });

    it("should list reports with filters", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      await listReports(1, 20, "pending", "song");

      expect(mockApiClient.get).toHaveBeenCalledWith("/reports", {
        params: { page: 1, page_size: 20, status: "pending", entity_type: "song" },
      });
    });
  });

  describe("getReport", () => {
    it("should fetch a single report by ID", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportResponse });

      const result = await getReport("report-123");

      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/reports/report-123"
      );
      expect(result).toEqual(mockReportResponse);
    });

    it("should throw error on API failure", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Not found"));

      await expect(getReport("invalid-id")).rejects.toThrow("Not found");
    });
  });

  describe("updateReport", () => {
    it("should update report status", async () => {
      const updatedReport = {
        ...mockReportResponse,
        status: "reviewed",
        reviewer_id: "admin-123",
        reviewed_at: "2024-12-02T00:00:00Z",
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedReport });

      const result = await updateReport("report-123", { status: "reviewed" as ReportStatus });

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/reports/report-123",
        { status: "reviewed" }
      );
      expect(result.status).toBe("reviewed");
    });

    it("should throw error on API failure", async () => {
      mockApiClient.patch.mockRejectedValueOnce(new Error("Update failed"));

      await expect(
        updateReport("report-123", { status: "reviewed" as ReportStatus })
      ).rejects.toThrow("Update failed");
    });
  });

  describe("deleteReport", () => {
    it("should delete a report", async () => {
      const deleteResponse = { message: "Report deleted", id: "report-123" };
      mockApiClient.delete.mockResolvedValueOnce({ data: deleteResponse });

      const result = await deleteReport("report-123");

      expect(mockApiClient.delete).toHaveBeenCalledWith(
        "/reports/report-123"
      );
      expect(result).toEqual(deleteResponse);
    });

    it("should throw error on API failure", async () => {
      mockApiClient.delete.mockRejectedValueOnce(new Error("Delete failed"));

      await expect(deleteReport("report-123")).rejects.toThrow("Delete failed");
    });
  });

  describe("useCreateReport hook", () => {
    const createRequest: CreateMetadataReportRequest = {
      entity_type: "artist",
      entity_id: "artist-123",
      field_name: "name",
      current_value: "Old Name",
      suggested_value: "New Name",
    };

    it("should create a report", async () => {
      mockApiClient.post.mockResolvedValueOnce({ data: mockReportResponse });

      const { result } = renderHook(() => useCreateReport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(createRequest);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.post).toHaveBeenCalledWith(
        "/reports",
        createRequest
      );
    });

    it("should handle creation error", async () => {
      mockApiClient.post.mockRejectedValueOnce(new Error("Creation failed"));

      const { result } = renderHook(() => useCreateReport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(createRequest);

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useMyReports hook", () => {
    it("should fetch user reports", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      const { result } = renderHook(() => useMyReports(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockReportListResponse);
    });

    it("should fetch with custom params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      const { result } = renderHook(() => useMyReports(2, 10, "reviewed"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.get).toHaveBeenCalledWith("/reports/me", {
        params: { page: 2, page_size: 10, status: "reviewed" },
      });
    });

    it("should handle error", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      const { result } = renderHook(() => useMyReports(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useReportsList hook", () => {
    it("should fetch reports list", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      const { result } = renderHook(() => useReportsList(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockReportListResponse);
    });

    it("should fetch with filters", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportListResponse });

      const { result } = renderHook(
        () => useReportsList(1, 20, "pending", "album"),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.get).toHaveBeenCalledWith("/reports", {
        params: { page: 1, page_size: 20, status: "pending", entity_type: "album" },
      });
    });
  });

  describe("useReport hook", () => {
    it("should fetch a single report", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockReportResponse });

      const { result } = renderHook(() => useReport("report-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockReportResponse);
    });

    it("should not fetch when report ID is undefined", async () => {
      const { result } = renderHook(() => useReport(undefined), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe("useUpdateReport hook", () => {
    it("should update report status", async () => {
      const updatedReport = { ...mockReportResponse, status: "fixed" };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedReport });

      const { result } = renderHook(() => useUpdateReport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        reportId: "report-123",
        request: { status: "fixed" as ReportStatus },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/reports/report-123",
        { status: "fixed" }
      );
    });

    it("should handle update error", async () => {
      mockApiClient.patch.mockRejectedValueOnce(new Error("Update failed"));

      const { result } = renderHook(() => useUpdateReport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        reportId: "report-123",
        request: { status: "reviewed" as ReportStatus },
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useDeleteReport hook", () => {
    it("should delete a report", async () => {
      const deleteResponse = { message: "Deleted", id: "report-123" };
      mockApiClient.delete.mockResolvedValueOnce({ data: deleteResponse });

      const { result } = renderHook(() => useDeleteReport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate("report-123");

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.delete).toHaveBeenCalledWith(
        "/reports/report-123"
      );
    });

    it("should handle delete error", async () => {
      mockApiClient.delete.mockRejectedValueOnce(new Error("Delete failed"));

      const { result } = renderHook(() => useDeleteReport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate("report-123");

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("toMetadataReport helper", () => {
    it("should convert API response to MetadataReport type", () => {
      const result = toMetadataReport(mockReportResponse);

      expect(result).toEqual({
        id: "report-123",
        entity_type: "song",
        entity_id: "song-456",
        reporter_id: "user-789",
        field_name: "name",
        current_value: "Wrong Name",
        suggested_value: "Correct Name",
        description: "The song name is incorrect",
        status: "pending",
        reviewed_by: null,
        reviewed_at: null,
        created_at: "2024-12-01T00:00:00Z",
      });
    });

    it("should handle reviewed report", () => {
      const reviewedReport: ReportResponse = {
        ...mockReportResponse,
        status: "reviewed",
        reviewer_id: "admin-123",
        reviewed_at: "2024-12-02T00:00:00Z",
      };

      const result = toMetadataReport(reviewedReport);

      expect(result.status).toBe("reviewed");
      expect(result.reviewed_by).toBe("admin-123");
      expect(result.reviewed_at).toBe("2024-12-02T00:00:00Z");
    });

    it("should handle null description", () => {
      const reportWithNullDesc: ReportResponse = {
        ...mockReportResponse,
        description: null,
      };

      const result = toMetadataReport(reportWithNullDesc);

      expect(result.description).toBeNull();
    });
  });
});
