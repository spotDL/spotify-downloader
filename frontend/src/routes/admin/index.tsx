import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/auth";
import { useSystemStats } from "@/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Spinner,
} from "@/components/ui";
import { StatCard, StatCardGrid } from "@/components/ui/stat-card";

export const Route = createFileRoute("/admin/")({
  component: AdminDashboard,
});

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toLocaleString();
}

function AdminDashboard() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { data: stats, isLoading, error } = useSystemStats();

  // Redirect non-admins
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/auth/login" });
    } else if (user && !user.is_admin) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, user, navigate]);

  if (!isAuthenticated || !user?.is_admin) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-accent-peak">Failed to load dashboard</p>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-50">
            Admin Dashboard
          </h1>
          <p className="text-zinc-400 mt-1">
            Manage users, matches, and system settings
          </p>
        </div>
        <Badge variant="warning" size="md">
          <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Admin Only
        </Badge>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/admin/users">
          <Card variant="bordered" hover className="h-full">
            <CardContent className="py-6 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-accent-needle/10 flex items-center justify-center text-accent-needle">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              <h3 className="font-medium text-zinc-200">Users</h3>
              <p className="text-sm text-zinc-500 mt-1">Manage accounts</p>
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/matches">
          <Card variant="bordered" hover className="h-full">
            <CardContent className="py-6 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-accent-cool/10 flex items-center justify-center text-accent-cool">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </div>
              <h3 className="font-medium text-zinc-200">Matches</h3>
              <p className="text-sm text-zinc-500 mt-1">Moderate matches</p>
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/reports">
          <Card variant="bordered" hover className="h-full">
            <CardContent className="py-6 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-accent-warm/10 flex items-center justify-center text-accent-warm">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="font-medium text-zinc-200">Reports</h3>
              <p className="text-sm text-zinc-500 mt-1">Review metadata</p>
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/import">
          <Card variant="bordered" hover className="h-full">
            <CardContent className="py-6 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-accent-safe/10 flex items-center justify-center text-accent-safe">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <h3 className="font-medium text-zinc-200">Import/Export</h3>
              <p className="text-sm text-zinc-500 mt-1">Manage data</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Entity Stats */}
      <section>
        <h2 className="text-lg font-semibold text-zinc-200 mb-4">
          Database Overview
        </h2>
        <StatCardGrid columns={3}>
          <StatCard
            label="Songs"
            value={formatNumber(stats?.entities.songs || 0)}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            }
            variant="success"
            trend={stats?.growth.songs_this_week ? { value: stats.growth.songs_this_week, label: "this week" } : undefined}
          />
          <StatCard
            label="Artists"
            value={formatNumber(stats?.entities.artists || 0)}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            }
            variant="warning"
          />
          <StatCard
            label="Albums"
            value={formatNumber(stats?.entities.albums || 0)}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            }
            variant="info"
          />
          <StatCard
            label="Playlists"
            value={formatNumber(stats?.entities.playlists || 0)}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            }
            variant="default"
          />
          <StatCard
            label="Matches"
            value={formatNumber(stats?.entities.matches || 0)}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            }
            variant="default"
            trend={stats?.growth.matches_this_week ? { value: stats.growth.matches_this_week, label: "this week" } : undefined}
          />
          <StatCard
            label="Users"
            value={formatNumber(stats?.entities.users || 0)}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            }
            variant="success"
            trend={stats?.growth.new_users_this_week ? { value: stats.growth.new_users_this_week, label: "this week" } : undefined}
          />
        </StatCardGrid>
      </section>

      {/* Growth & Cache Stats */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Growth Today */}
        <Card variant="bordered">
          <CardHeader className="border-b border-zinc-800/50">
            <CardTitle className="flex items-center gap-2">
              <svg className="w-5 h-5 text-accent-safe" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              Today's Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">New Songs</span>
                <span className="font-mono text-zinc-200">
                  +{stats?.growth.songs_today || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">New Matches</span>
                <span className="font-mono text-zinc-200">
                  +{stats?.growth.matches_today || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">New Users</span>
                <span className="font-mono text-zinc-200">
                  +{stats?.growth.new_users_today || 0}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cache Stats */}
        <Card variant="bordered">
          <CardHeader className="border-b border-zinc-800/50">
            <CardTitle className="flex items-center gap-2">
              <svg className="w-5 h-5 text-accent-cool" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              Cache Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Hit Rate</span>
                <Badge variant={stats?.cache.hit_rate && stats.cache.hit_rate > 0.8 ? "success" : "warning"}>
                  {((stats?.cache.hit_rate || 0) * 100).toFixed(1)}%
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Cache Size</span>
                <span className="font-mono text-zinc-200">
                  {stats?.cache.size_mb?.toFixed(1) || 0} MB
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Entries</span>
                <span className="font-mono text-zinc-200">
                  {formatNumber(stats?.cache.entries || 0)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
