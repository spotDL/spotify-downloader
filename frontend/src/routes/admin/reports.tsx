import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/stores/auth";
import { useReportsList, useUpdateReport } from "@/api";
import {
  Card,
  CardContent,
  Badge,
  Button,
  Select,
  Spinner,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import type { MetadataReportStatus, MetadataReportEntityType } from "@/types";

export const Route = createFileRoute("/admin/reports")({
  component: AdminReportsPage,
});

function AdminReportsPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { addToast } = useToast();

  const [filters, setFilters] = useState<{
    page: number;
    page_size: number;
    status?: MetadataReportStatus;
    entity_type?: MetadataReportEntityType;
  }>({
    page: 1,
    page_size: 20,
  });

  const { data, isLoading, error } = useReportsList(
    filters.page,
    filters.page_size,
    filters.status,
    filters.entity_type
  );
  const updateReportMutation = useUpdateReport();

  // Redirect non-admins
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/auth/login" });
    } else if (user && !user.is_admin) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, user, navigate]);

  const handleUpdateStatus = async (reportId: string, status: MetadataReportStatus) => {
    try {
      await updateReportMutation.mutateAsync({
        reportId,
        request: { status },
      });
      addToast(`Report marked as ${status}`, "success");
    } catch (err) {
      addToast("Failed to update report", "error");
    }
  };

  if (!isAuthenticated || !user?.is_admin) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "fixed":
        return <Badge variant="success" size="sm">Fixed</Badge>;
      case "dismissed":
        return <Badge variant="error" size="sm">Dismissed</Badge>;
      case "reviewed":
        return <Badge variant="info" size="sm">Reviewed</Badge>;
      default:
        return <Badge variant="warning" size="sm">Pending</Badge>;
    }
  };

  const getEntityTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      song: "accent-safe",
      artist: "accent-needle",
      album: "accent-cool",
      playlist: "accent-warm",
    };
    return (
      <Badge variant="muted" size="sm" className={`text-${colors[type] || "zinc"}`}>
        {type}
      </Badge>
    );
  };

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Metadata Reports</h1>
          <p className="text-zinc-400 mt-1">
            {data?.total || 0} total reports
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select
          options={[
            { value: "", label: "All Status" },
            { value: "pending", label: "Pending" },
            { value: "reviewed", label: "Reviewed" },
            { value: "fixed", label: "Fixed" },
            { value: "dismissed", label: "Dismissed" },
          ]}
          value={filters.status || ""}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              status: (e.target.value as MetadataReportStatus) || undefined,
              page: 1,
            }))
          }
          className="w-36"
        />
        <Select
          options={[
            { value: "", label: "All Types" },
            { value: "song", label: "Songs" },
            { value: "artist", label: "Artists" },
            { value: "album", label: "Albums" },
            { value: "playlist", label: "Playlists" },
          ]}
          value={filters.entity_type || ""}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              entity_type: (e.target.value as MetadataReportEntityType) || undefined,
              page: 1,
            }))
          }
          className="w-36"
        />
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}

      {/* Error */}
      {error && (
        <Card variant="bordered" className="border-red-900/50">
          <CardContent className="py-6 text-center">
            <p className="text-accent-peak">Failed to load reports</p>
          </CardContent>
        </Card>
      )}

      {/* Report List */}
      {!isLoading && !error && data && (
        <div className="space-y-4">
          {data.reports.map((report) => (
            <Card key={report.id} variant="bordered" className="overflow-hidden">
              <CardContent className="py-4">
                <div className="flex items-start gap-4">
                  {/* Report Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-3">
                      {getStatusBadge(report.status)}
                      {getEntityTypeBadge(report.entity_type)}
                      <span className="text-xs text-zinc-500">
                        {new Date(report.created_at).toLocaleString()}
                      </span>
                    </div>

                    {/* Field being reported */}
                    <div className="mb-3">
                      <p className="text-sm text-zinc-400 mb-1">
                        Field: <span className="font-mono text-zinc-300">{report.field_name}</span>
                      </p>
                    </div>

                    {/* Values comparison */}
                    <div className="grid md:grid-cols-2 gap-4 mb-3">
                      <div className="p-3 rounded-lg bg-accent-peak/10 border border-accent-peak/20">
                        <p className="text-xs text-accent-peak uppercase tracking-wide mb-1">
                          Current Value
                        </p>
                        <p className="text-sm text-zinc-300 break-words">
                          {report.current_value || "(empty)"}
                        </p>
                      </div>
                      <div className="p-3 rounded-lg bg-accent-safe/10 border border-accent-safe/20">
                        <p className="text-xs text-accent-safe uppercase tracking-wide mb-1">
                          Suggested Value
                        </p>
                        <p className="text-sm text-zinc-300 break-words">
                          {report.suggested_value || "(empty)"}
                        </p>
                      </div>
                    </div>

                    {/* Description */}
                    {report.description && (
                      <div className="mb-3">
                        <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">
                          Description
                        </p>
                        <p className="text-sm text-zinc-400">
                          {report.description}
                        </p>
                      </div>
                    )}

                    {/* Reporter info */}
                    <div className="text-sm text-zinc-500">
                      Reported by <span className="text-zinc-400">{report.reporter_username || report.reporter_id}</span>
                      {report.reviewed_by_username && (
                        <span>
                          {" "}| Reviewed by <span className="text-zinc-400">{report.reviewed_by_username}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="shrink-0 flex flex-col gap-2">
                    {report.status === "pending" && (
                      <>
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => handleUpdateStatus(report.id, "fixed")}
                          isLoading={updateReportMutation.isPending}
                        >
                          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Mark Fixed
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleUpdateStatus(report.id, "reviewed")}
                          isLoading={updateReportMutation.isPending}
                        >
                          Mark Reviewed
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleUpdateStatus(report.id, "dismissed")}
                          isLoading={updateReportMutation.isPending}
                          className="text-accent-peak"
                        >
                          Dismiss
                        </Button>
                      </>
                    )}
                    {report.status !== "pending" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleUpdateStatus(report.id, "pending")}
                        isLoading={updateReportMutation.isPending}
                      >
                        Reopen
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Pagination */}
          {data.total > data.page_size && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-400">
                Page {data.page} of {Math.ceil(data.total / data.page_size)}
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={data.page <= 1}
                  onClick={() =>
                    setFilters((prev) => ({ ...prev, page: prev.page - 1 }))
                  }
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={data.page >= Math.ceil(data.total / data.page_size)}
                  onClick={() =>
                    setFilters((prev) => ({ ...prev, page: prev.page + 1 }))
                  }
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && data?.reports.length === 0 && (
        <Card variant="bordered">
          <CardContent className="py-12 text-center">
            <p className="text-zinc-400">No reports found</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
