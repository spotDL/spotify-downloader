import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/stores/auth";
import { useAdminUsers, useUpdateAdminUser } from "@/api";
import {
  Card,
  CardContent,
  Badge,
  Button,
  Input,
  Select,
  Spinner,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import type { AdminUserListRequest } from "@/types";

export const Route = createFileRoute("/admin/users")({
  component: AdminUsersPage,
});

function AdminUsersPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { addToast } = useToast();

  const [filters, setFilters] = useState<AdminUserListRequest>({
    page: 1,
    per_page: 20,
    sort_by: "created_at",
    sort_order: "desc",
  });
  const [searchInput, setSearchInput] = useState("");

  const { data, isLoading, error } = useAdminUsers(filters);
  const updateUserMutation = useUpdateAdminUser();

  // Redirect non-admins
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/auth/login" });
    } else if (user && !user.is_admin) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, user, navigate]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters((prev) => ({
      ...prev,
      search: searchInput || undefined,
      page: 1,
    }));
  };

  const handleToggleAdmin = async (userId: string, currentValue: boolean) => {
    try {
      await updateUserMutation.mutateAsync({
        userId,
        data: { is_admin: !currentValue },
      });
      addToast(`User ${currentValue ? "demoted from" : "promoted to"} admin`, "success");
    } catch (err) {
      addToast("Failed to update user", "error");
    }
  };

  const handleToggleActive = async (userId: string, currentValue: boolean) => {
    try {
      await updateUserMutation.mutateAsync({
        userId,
        data: { is_active: !currentValue },
      });
      addToast(`User ${currentValue ? "disabled" : "enabled"}`, "success");
    } catch (err) {
      addToast("Failed to update user", "error");
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">User Management</h1>
          <p className="text-zinc-400 mt-1">
            {data?.total || 0} total users
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card variant="bordered">
        <CardContent className="py-4">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <Input
                type="text"
                placeholder="Search by username or email..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <Select
              options={[
                { value: "", label: "All Users" },
                { value: "true", label: "Admins Only" },
                { value: "false", label: "Non-Admins" },
              ]}
              value={filters.is_admin?.toString() || ""}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  is_admin: e.target.value ? e.target.value === "true" : undefined,
                  page: 1,
                }))
              }
              className="w-36"
            />
            <Select
              options={[
                { value: "", label: "All Status" },
                { value: "true", label: "Active" },
                { value: "false", label: "Inactive" },
              ]}
              value={filters.is_active?.toString() || ""}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  is_active: e.target.value ? e.target.value === "true" : undefined,
                  page: 1,
                }))
              }
              className="w-36"
            />
            <Select
              options={[
                { value: "created_at", label: "Join Date" },
                { value: "username", label: "Username" },
                { value: "reputation_score", label: "Reputation" },
              ]}
              value={filters.sort_by || "created_at"}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  sort_by: e.target.value as any,
                }))
              }
              className="w-36"
            />
            <Button type="submit">Search</Button>
          </form>
        </CardContent>
      </Card>

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
            <p className="text-accent-peak">Failed to load users</p>
          </CardContent>
        </Card>
      )}

      {/* User List */}
      {!isLoading && !error && data && (
        <Card variant="bordered">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-zinc-800">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-zinc-400">
                    User
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-zinc-400">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-zinc-400">
                    Reputation
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-zinc-400">
                    Activity
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-zinc-400">
                    Joined
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-zinc-400">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {data.users.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-needle to-accent-warm flex items-center justify-center text-sm font-bold text-white">
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-zinc-200">{u.username}</p>
                          <p className="text-sm text-zinc-500">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {u.is_admin && (
                          <Badge variant="warning" size="sm">Admin</Badge>
                        )}
                        <Badge
                          variant={u.is_active ? "success" : "error"}
                          size="sm"
                        >
                          {u.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-zinc-300">
                        {u.reputation_score}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm text-zinc-400">
                        <p>{u.matches_submitted} matches</p>
                        <p>{u.votes_cast} votes</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-400">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "Unknown"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        {u.id !== user.id && (
                          <>
                            <Button
                              size="sm"
                              variant={u.is_admin ? "outline" : "secondary"}
                              onClick={() => handleToggleAdmin(u.id, u.is_admin)}
                              isLoading={updateUserMutation.isPending}
                            >
                              {u.is_admin ? "Remove Admin" : "Make Admin"}
                            </Button>
                            <Button
                              size="sm"
                              variant={u.is_active ? "ghost" : "primary"}
                              onClick={() => handleToggleActive(u.id, u.is_active)}
                              isLoading={updateUserMutation.isPending}
                            >
                              {u.is_active ? "Disable" : "Enable"}
                            </Button>
                          </>
                        )}
                        {u.id === user.id && (
                          <Badge variant="muted" size="sm">You</Badge>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800">
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
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !error && data?.users.length === 0 && (
        <Card variant="bordered">
          <CardContent className="py-12 text-center">
            <p className="text-zinc-400">No users found</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
