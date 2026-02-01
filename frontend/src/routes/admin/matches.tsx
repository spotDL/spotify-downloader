import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/stores/auth";
import { useAdminMatches, useUpdateMatchStatus, type MatchStatus } from "@/api";
import {
  Card,
  CardContent,
  Badge,
  Button,
  Select,
  Spinner,
} from "@/components/ui";
import { MatchScoreGauge } from "@/components/ui/match-gauge";
import { useToast } from "@/components/ui/toast";
import type { AdminMatchListRequest } from "@/types";

export const Route = createFileRoute("/admin/matches")({
  component: AdminMatchesPage,
});

function AdminMatchesPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { addToast } = useToast();

  const [filters, setFilters] = useState<AdminMatchListRequest>({
    page: 1,
    per_page: 20,
  });

  const { data, isLoading, error } = useAdminMatches(filters);
  const updateStatusMutation = useUpdateMatchStatus();

  // Redirect non-admins
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/auth/login" });
    } else if (user && !user.is_admin) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, user, navigate]);

  const handleUpdateStatus = async (matchId: string, status: MatchStatus) => {
    try {
      await updateStatusMutation.mutateAsync({
        matchId,
        data: { status },
      });
      addToast(`Match ${status}`, status === "verified" ? "success" : status === "rejected" ? "error" : "info");
    } catch (err) {
      addToast("Failed to update match", "error");
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
      case "verified":
        return <Badge variant="success" size="sm">Verified</Badge>;
      case "rejected":
        return <Badge variant="error" size="sm">Rejected</Badge>;
      default:
        return <Badge variant="warning" size="sm">Pending</Badge>;
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Match Moderation</h1>
          <p className="text-zinc-400 mt-1">
            {data?.total || 0} total matches
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select
          options={[
            { value: "", label: "All Status" },
            { value: "pending", label: "Pending" },
            { value: "verified", label: "Verified" },
            { value: "rejected", label: "Rejected" },
          ]}
          value={filters.status || ""}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              status: (e.target.value as MatchStatus) || undefined,
              page: 1,
            }))
          }
          className="w-36"
        />
        <Select
          options={[
            { value: "", label: "All Types" },
            { value: "system", label: "System" },
            { value: "user", label: "User Submitted" },
          ]}
          value={filters.match_type || ""}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              match_type: (e.target.value as "system" | "user") || undefined,
              page: 1,
            }))
          }
          className="w-40"
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
            <p className="text-accent-peak">Failed to load matches</p>
          </CardContent>
        </Card>
      )}

      {/* Match List */}
      {!isLoading && !error && data && (
        <div className="space-y-4">
          {data.matches.map((match) => (
            <Card key={match.id} variant="bordered" className="overflow-hidden">
              <CardContent className="py-4">
                <div className="flex items-start gap-4">
                  {/* Score */}
                  <div className="shrink-0">
                    <MatchScoreGauge
                      score={match.score || 0}
                      size="md"
                    />
                  </div>

                  {/* Match Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      {getStatusBadge(match.status || "pending")}
                      <Badge variant="muted" size="sm">
                        {match.match_type}
                      </Badge>
                      <span className="text-xs text-zinc-500">
                        {match.created_at ? new Date(match.created_at).toLocaleString() : "Unknown"}
                      </span>
                    </div>

                    {/* Source */}
                    <div className="mb-3">
                      <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">
                        Source ({match.source_platform})
                      </p>
                      <a
                        href={match.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-zinc-300 hover:text-accent-needle truncate block"
                      >
                        {match.source_url}
                      </a>
                    </div>

                    {/* Target */}
                    <div className="mb-3">
                      <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">
                        Target ({match.target_platform})
                      </p>
                      <a
                        href={match.target_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-zinc-300 hover:text-accent-needle truncate block"
                      >
                        {match.target_url}
                      </a>
                    </div>

                    {/* Votes & Submitter */}
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-accent-safe">+{match.upvotes}</span>
                        <span className="text-zinc-500">/</span>
                        <span className="text-accent-peak">-{match.downvotes}</span>
                      </div>
                      {match.submitted_by_username && (
                        <span className="text-zinc-500">
                          by <span className="text-zinc-400">{match.submitted_by_username}</span>
                        </span>
                      )}
                      {match.verified_by_username && (
                        <span className="text-zinc-500">
                          verified by <span className="text-zinc-400">{match.verified_by_username}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="shrink-0 flex flex-col gap-2">
                    {match.status !== "verified" && match.id && (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => handleUpdateStatus(match.id!, "verified")}
                        isLoading={updateStatusMutation.isPending}
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Verify
                      </Button>
                    )}
                    {match.status !== "rejected" && match.id && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleUpdateStatus(match.id!, "rejected")}
                        isLoading={updateStatusMutation.isPending}
                        className="text-accent-peak border-accent-peak/30 hover:bg-accent-peak/10"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Reject
                      </Button>
                    )}
                    {match.status !== "pending" && match.id && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleUpdateStatus(match.id!, "pending")}
                        isLoading={updateStatusMutation.isPending}
                      >
                        Reset
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-400">
                Page {data.page} of {data.total_pages}
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={data.page <= 1}
                  onClick={() =>
                    setFilters((prev) => ({ ...prev, page: (prev.page || 1) - 1 }))
                  }
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={data.page >= data.total_pages}
                  onClick={() =>
                    setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))
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
      {!isLoading && !error && data?.matches.length === 0 && (
        <Card variant="bordered">
          <CardContent className="py-12 text-center">
            <p className="text-zinc-400">No matches found</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
