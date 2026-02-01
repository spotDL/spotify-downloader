import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth";
import {
  useClearCache,
  useExportMatches,
  useExportUsers,
  useExportStatistics,
  type MatchStatus,
} from "@/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Select,
  Spinner,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";

export const Route = createFileRoute("/admin/import")({
  component: AdminImportPage,
});

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function AdminImportPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { addToast } = useToast();

  const [matchExportStatus, setMatchExportStatus] = useState<MatchStatus | "">(
    ""
  );

  const clearCacheMutation = useClearCache();
  const exportMatchesMutation = useExportMatches();
  const exportUsersMutation = useExportUsers();
  const exportStatsMutation = useExportStatistics();

  // Redirect non-admins
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/auth/login" });
    } else if (user && !user.is_admin) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, user, navigate]);

  const handleClearCache = async (
    cacheType: "all" | "search" | "entities" | "matches"
  ) => {
    try {
      await clearCacheMutation.mutateAsync({ cache_type: cacheType });
      addToast(
        `${cacheType === "all" ? "All caches" : `${cacheType} cache`} cleared successfully`,
        "success"
      );
    } catch (err) {
      addToast("Failed to clear cache", "error");
    }
  };

  const handleExportMatches = async () => {
    try {
      const data = await exportMatchesMutation.mutateAsync(
        matchExportStatus || undefined
      );
      downloadJson(
        data,
        `matches-export-${matchExportStatus || "verified"}-${new Date().toISOString().split("T")[0]}.json`
      );
      addToast(`Exported ${data.count} matches`, "success");
    } catch (err) {
      addToast("Failed to export matches", "error");
    }
  };

  const handleExportUsers = async () => {
    try {
      const data = await exportUsersMutation.mutateAsync();
      downloadJson(
        data,
        `users-export-${new Date().toISOString().split("T")[0]}.json`
      );
      addToast(`Exported ${data.count} users`, "success");
    } catch (err) {
      addToast("Failed to export users", "error");
    }
  };

  const handleExportStats = async () => {
    try {
      const data = await exportStatsMutation.mutateAsync();
      downloadJson(
        data,
        `statistics-export-${new Date().toISOString().split("T")[0]}.json`
      );
      addToast("Statistics exported successfully", "success");
    } catch (err) {
      addToast("Failed to export statistics", "error");
    }
  };

  if (!isAuthenticated || !user?.is_admin) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-50">Import / Export Tools</h1>
        <p className="text-zinc-400 mt-1">Manage data and cache operations</p>
      </div>

      {/* Cache Management */}
      <Card variant="bordered">
        <CardHeader className="border-b border-zinc-800/50">
          <CardTitle className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-accent-cool"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
            Cache Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-400 mb-4">
            Clear cached data to force fresh lookups. This is useful when
            debugging or after database changes.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button
              variant="outline"
              onClick={() => handleClearCache("all")}
              isLoading={clearCacheMutation.isPending}
              className="justify-start"
            >
              <svg
                className="w-4 h-4 mr-2 text-accent-peak"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              Clear All Caches
            </Button>
            <Button
              variant="outline"
              onClick={() => handleClearCache("search")}
              isLoading={clearCacheMutation.isPending}
              className="justify-start"
            >
              <svg
                className="w-4 h-4 mr-2 text-accent-needle"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              Clear Search Cache
            </Button>
            <Button
              variant="outline"
              onClick={() => handleClearCache("entities")}
              isLoading={clearCacheMutation.isPending}
              className="justify-start"
            >
              <svg
                className="w-4 h-4 mr-2 text-accent-safe"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                />
              </svg>
              Clear Entity Cache
            </Button>
            <Button
              variant="outline"
              onClick={() => handleClearCache("matches")}
              isLoading={clearCacheMutation.isPending}
              className="justify-start"
            >
              <svg
                className="w-4 h-4 mr-2 text-accent-cool"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                />
              </svg>
              Clear Match Cache
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Export Options */}
      <Card variant="bordered">
        <CardHeader className="border-b border-zinc-800/50">
          <CardTitle className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-accent-safe"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Export Data
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-400 mb-4">
            Export data for backup or migration purposes. All exports are in
            JSON format.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Matches Export
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Export matches filtered by status
                </p>
                <div className="flex gap-2">
                  <Select
                    options={[
                      { value: "", label: "Verified (default)" },
                      { value: "pending", label: "Pending" },
                      { value: "rejected", label: "Rejected" },
                    ]}
                    value={matchExportStatus}
                    onChange={(e) =>
                      setMatchExportStatus(e.target.value as MatchStatus | "")
                    }
                    className="flex-1"
                  />
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleExportMatches}
                    isLoading={exportMatchesMutation.isPending}
                  >
                    Export
                  </Button>
                </div>
              </CardContent>
            </Card>
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">Users Export</h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Export user data (no emails/passwords)
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleExportUsers}
                  isLoading={exportUsersMutation.isPending}
                >
                  Export Users
                </Button>
              </CardContent>
            </Card>
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Statistics Export
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Export analytics and statistics
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleExportStats}
                  isLoading={exportStatsMutation.isPending}
                >
                  Export Stats
                </Button>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Import Options */}
      <Card variant="bordered">
        <CardHeader className="border-b border-zinc-800/50">
          <CardTitle className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-accent-needle"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
            Import Data
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-400 mb-4">
            Import data from backups or other sources.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Matches Import
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Import matches from JSON file
                </p>
                <Button variant="outline" size="sm" disabled>
                  Coming Soon
                </Button>
              </CardContent>
            </Card>
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Bulk URL Import
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Import songs from URL list
                </p>
                <Button variant="outline" size="sm" disabled>
                  Coming Soon
                </Button>
              </CardContent>
            </Card>
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Database Restore
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Restore from backup file
                </p>
                <Button variant="outline" size="sm" disabled>
                  Coming Soon
                </Button>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card variant="bordered" className="border-accent-peak/30">
        <CardHeader className="border-b border-accent-peak/20">
          <CardTitle className="flex items-center gap-2 text-accent-peak">
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-400 mb-4">
            These actions are irreversible. Please proceed with caution.
          </p>
          <div className="flex flex-wrap gap-4">
            <Button
              variant="outline"
              disabled
              className="border-accent-peak/30 text-accent-peak hover:bg-accent-peak/10"
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              Purge Unverified Matches (Coming Soon)
            </Button>
            <Button
              variant="outline"
              disabled
              className="border-accent-peak/30 text-accent-peak hover:bg-accent-peak/10"
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              Reset Database (Coming Soon)
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
