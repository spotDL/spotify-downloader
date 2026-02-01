import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import { useAuthStore } from "@/stores/auth";
import {
  useExportMatches,
  useExportUsers,
  useExportStatistics,
  useImportMatches,
  useImportUrls,
  usePurgeUnverifiedMatches,
  useResetDatabase,
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
  Input,
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
  const [urlInput, setUrlInput] = useState("");
  const [purgePreview, setPurgePreview] = useState<{
    pending: number;
    rejected: number;
  } | null>(null);
  const [resetPreview, setResetPreview] = useState<{
    songs: number;
    matches: number;
  } | null>(null);
  const [confirmReset, setConfirmReset] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const exportMatchesMutation = useExportMatches();
  const exportUsersMutation = useExportUsers();
  const exportStatsMutation = useExportStatistics();
  const importMatchesMutation = useImportMatches();
  const importUrlsMutation = useImportUrls();
  const purgeMutation = usePurgeUnverifiedMatches();
  const resetMutation = useResetDatabase();

  // Redirect non-admins
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/auth/login" });
    } else if (user && !user.is_admin) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, user, navigate]);

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

  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);

      if (!data.matches || !Array.isArray(data.matches)) {
        addToast("Invalid file format - expected { matches: [...] }", "error");
        return;
      }

      const result = await importMatchesMutation.mutateAsync({
        matches: data.matches,
      });
      addToast(
        `Imported ${result.imported} matches (${result.skipped} skipped)`,
        "success"
      );
    } catch (err) {
      addToast("Failed to import matches", "error");
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleBulkUrlImport = async () => {
    const urls = urlInput
      .split("\n")
      .map((u) => u.trim())
      .filter((u) => u.length > 0);

    if (urls.length === 0) {
      addToast("Please enter at least one URL", "error");
      return;
    }

    try {
      const result = await importUrlsMutation.mutateAsync({ urls });
      addToast(`Queued ${result.queued} URLs for import`, "success");
      setUrlInput("");
    } catch (err) {
      addToast("Failed to queue URLs", "error");
    }
  };

  const handlePurgePreview = async () => {
    try {
      const result = await purgeMutation.mutateAsync(false);
      setPurgePreview({
        pending: result.pending_matches || 0,
        rejected: result.rejected_matches || 0,
      });
    } catch (err) {
      addToast("Failed to get purge preview", "error");
    }
  };

  const handlePurgeConfirm = async () => {
    try {
      const result = await purgeMutation.mutateAsync(true);
      addToast(`Purged ${result.deleted} unverified matches`, "success");
      setPurgePreview(null);
    } catch (err) {
      addToast("Failed to purge matches", "error");
    }
  };

  const handleResetPreview = async () => {
    try {
      const result = await resetMutation.mutateAsync("");
      setResetPreview({
        songs: result.songs_to_delete || 0,
        matches: result.matches_to_delete || 0,
      });
    } catch (err) {
      addToast("Failed to get reset preview", "error");
    }
  };

  const handleResetConfirm = async () => {
    if (confirmReset !== "RESET") {
      addToast('Type "RESET" to confirm', "error");
      return;
    }

    try {
      await resetMutation.mutateAsync("RESET");
      addToast("Database reset complete", "success");
      setResetPreview(null);
      setConfirmReset("");
    } catch (err) {
      addToast("Failed to reset database", "error");
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
        <p className="text-zinc-400 mt-1">Manage data operations</p>
      </div>

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
          <div className="grid sm:grid-cols-2 gap-4">
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Matches Import
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Import matches from JSON file
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleFileImport}
                  className="hidden"
                  id="match-file-input"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  isLoading={importMatchesMutation.isPending}
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
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  Choose File
                </Button>
              </CardContent>
            </Card>
            <Card variant="bordered" className="bg-zinc-900/50">
              <CardContent className="py-4">
                <h4 className="font-medium text-zinc-200 mb-1">
                  Bulk URL Import
                </h4>
                <p className="text-sm text-zinc-500 mb-3">
                  Import songs from URL list (one per line)
                </p>
                <textarea
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://open.spotify.com/track/...&#10;https://open.spotify.com/album/..."
                  rows={4}
                  className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-200 text-sm placeholder-zinc-500 focus:border-accent-needle focus:outline-none resize-none mb-3"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkUrlImport}
                  isLoading={importUrlsMutation.isPending}
                  disabled={!urlInput.trim()}
                >
                  Queue Import
                </Button>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card variant="bordered" className="border-red-500/30 bg-red-950/5">
        <CardHeader className="border-b border-red-500/20">
          <CardTitle className="flex items-center gap-3 text-red-400">
            <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
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
            </div>
            <div>
              <span>Danger Zone</span>
              <p className="text-sm font-normal text-zinc-500 mt-0.5">
                These actions are irreversible. Please proceed with caution.
              </p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Purge Unverified Matches */}
          <div className={`relative rounded-xl border transition-all ${
            purgePreview
              ? "border-red-500/40 bg-red-950/20"
              : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
          }`}>
            <div className="p-5">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-zinc-100 mb-1">
                    Purge Unverified Matches
                  </h4>
                  <p className="text-sm text-zinc-400">
                    Delete all pending and rejected matches from the database. Verified matches will remain.
                  </p>

                  {purgePreview && (
                    <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                      <div className="flex items-center gap-2 text-red-300 text-sm font-medium mb-2">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Deletion Preview
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <div className="text-center p-2 rounded bg-zinc-900/50">
                          <div className="text-lg font-bold text-amber-400">{purgePreview.pending}</div>
                          <div className="text-xs text-zinc-500">Pending</div>
                        </div>
                        <div className="text-center p-2 rounded bg-zinc-900/50">
                          <div className="text-lg font-bold text-red-400">{purgePreview.rejected}</div>
                          <div className="text-xs text-zinc-500">Rejected</div>
                        </div>
                        <div className="text-center p-2 rounded bg-zinc-900/50">
                          <div className="text-lg font-bold text-red-300">{purgePreview.pending + purgePreview.rejected}</div>
                          <div className="text-xs text-zinc-500">Total</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {!purgePreview ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePurgePreview}
                      isLoading={purgeMutation.isPending}
                    >
                      Preview
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setPurgePreview(null)}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={handlePurgeConfirm}
                        isLoading={purgeMutation.isPending}
                        className="bg-red-500 hover:bg-red-600 text-white border-0"
                      >
                        Confirm Purge
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Reset Database */}
          <div className={`relative rounded-xl border transition-all ${
            resetPreview
              ? "border-red-500/40 bg-red-950/20"
              : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
          }`}>
            <div className="p-5">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-zinc-100 mb-1">
                    Reset Database
                  </h4>
                  <p className="text-sm text-zinc-400">
                    Delete ALL songs, artists, albums, playlists, and matches. User accounts will be preserved.
                  </p>

                  {resetPreview && (
                    <div className="mt-4 space-y-3">
                      <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                        <div className="flex items-center gap-2 text-red-300 text-sm font-medium mb-2">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          Deletion Preview
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div className="text-center p-2 rounded bg-zinc-900/50">
                            <div className="text-lg font-bold text-red-400">{resetPreview.songs.toLocaleString()}</div>
                            <div className="text-xs text-zinc-500">Songs</div>
                          </div>
                          <div className="text-center p-2 rounded bg-zinc-900/50">
                            <div className="text-lg font-bold text-red-400">{resetPreview.matches.toLocaleString()}</div>
                            <div className="text-xs text-zinc-500">Matches</div>
                          </div>
                        </div>
                        <p className="text-xs text-zinc-500 mt-2 text-center">
                          + all related artists, albums, and playlists
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <Input
                          type="text"
                          placeholder='Type "RESET" to confirm'
                          value={confirmReset}
                          onChange={(e) => setConfirmReset(e.target.value.toUpperCase())}
                          className="w-48 font-mono"
                        />
                        {confirmReset === "RESET" && (
                          <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {!resetPreview ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleResetPreview}
                      isLoading={resetMutation.isPending}
                    >
                      Preview
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setResetPreview(null);
                          setConfirmReset("");
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleResetConfirm}
                        isLoading={resetMutation.isPending}
                        disabled={confirmReset !== "RESET"}
                        className="bg-red-500 hover:bg-red-600 text-white border-0 disabled:bg-zinc-700 disabled:text-zinc-400"
                      >
                        Reset Database
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
