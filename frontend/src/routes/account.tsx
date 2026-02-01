import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { useLogout } from "@/api/auth";
import {
  Button,
  Input,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Badge,
} from "@/components/ui";

export const Route = createFileRoute("/account")({
  beforeLoad: () => {
    const { isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated) {
      throw redirect({
        to: "/auth/login",
        search: {
          redirect: "/account",
        },
      });
    }
  },
  component: AccountPage,
});

// Icons
const UserIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const ShieldIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const StarIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
  </svg>
);

const TrashIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

// Section header component
function SectionHeader({
  icon,
  iconBg,
  iconColor,
  title,
  description,
}: {
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl ${iconBg} flex items-center justify-center`}>
        <span className={iconColor}>{icon}</span>
      </div>
      <div>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </div>
    </div>
  );
}

function AccountPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const logoutMutation = useLogout();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // User is guaranteed to exist due to beforeLoad check
  if (!user) return null;

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
    navigate({ to: "/auth/login" });
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      // TODO: Show error toast
      return;
    }
    // TODO: Implement password change API
    console.log("Password change not implemented yet");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  // Get user initials for avatar
  const getUserInitials = (username: string) => {
    return username.slice(0, 2).toUpperCase();
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Account Settings
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Manage your account information and preferences
        </p>
      </div>

      {/* Profile Section */}
      <Card>
        <CardHeader>
          <SectionHeader
            icon={<UserIcon />}
            iconBg="bg-[var(--accent-safe)]/10"
            iconColor="text-[var(--accent-safe)]"
            title="Profile"
            description="Your account information"
          />
        </CardHeader>
        <CardContent className="space-y-6">
          {/* User avatar and basic info */}
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--accent-safe)] to-[var(--accent-cool)] flex items-center justify-center">
              <span className="text-xl font-bold text-white">
                {getUserInitials(user.username)}
              </span>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
                  {user.username}
                </h3>
                {user.is_admin && (
                  <Badge variant="premium" size="sm">Admin</Badge>
                )}
              </div>
              <p className="text-sm text-[var(--color-text-muted)]">{user.email}</p>
            </div>
          </div>

          {/* Account details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-[var(--color-border-subtle)]">
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                Username
              </label>
              <Input value={user.username} disabled />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                Email
              </label>
              <Input value={user.email} disabled />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                Member Since
              </label>
              <Input value={formatDate(user.created_at)} disabled />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                Account Status
              </label>
              <div className="flex items-center gap-2 h-10 px-3">
                <div className={`w-2 h-2 rounded-full ${user.is_active ? "bg-green-500" : "bg-red-500"}`} />
                <span className="text-sm text-[var(--color-text-secondary)]">
                  {user.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reputation Section */}
      <Card>
        <CardHeader>
          <SectionHeader
            icon={<StarIcon />}
            iconBg="bg-[var(--accent-warm)]/10"
            iconColor="text-[var(--accent-warm)]"
            title="Reputation"
            description="Your contribution score"
          />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <div className="text-3xl font-bold text-[var(--color-text-primary)]">
                {user.reputation_score}
              </div>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">
                Reputation Points
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-[var(--color-text-dim)]">
                Earn points by submitting verified matches and voting on community contributions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Security Section */}
      <Card>
        <CardHeader>
          <SectionHeader
            icon={<ShieldIcon />}
            iconBg="bg-blue-500/10"
            iconColor="text-blue-400"
            title="Security"
            description="Password and security settings"
          />
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                Current Password
              </label>
              <Input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                  New Password
                </label>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                  Confirm New Password
                </label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={!currentPassword || !newPassword || !confirmPassword}
              >
                Update Password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Session Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <SectionHeader
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              }
              iconBg="bg-purple-500/10"
              iconColor="text-purple-400"
              title="Session"
              description="Manage your current session"
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Signed in as <span className="font-medium">{user.username}</span>
              </p>
              <p className="text-xs text-[var(--color-text-dim)] mt-1">
                Logging out will end your current session on this device.
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={handleLogout}
              disabled={logoutMutation.isPending}
            >
              {logoutMutation.isPending ? "Logging out..." : "Log Out"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-500/20">
        <CardHeader>
          <SectionHeader
            icon={<TrashIcon />}
            iconBg="bg-red-500/10"
            iconColor="text-red-400"
            title="Danger Zone"
            description="Irreversible actions"
          />
        </CardHeader>
        <CardContent>
          {!showDeleteConfirm ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--color-text-secondary)]">Delete Account</p>
                <p className="text-xs text-[var(--color-text-dim)] mt-1">
                  Permanently delete your account and all associated data.
                </p>
              </div>
              <Button
                variant="ghost"
                onClick={() => setShowDeleteConfirm(true)}
                className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
              >
                Delete Account
              </Button>
            </div>
          ) : (
            <div className="space-y-4 p-4 bg-red-500/5 rounded-lg border border-red-500/20">
              <p className="text-sm text-red-400">
                Are you sure you want to delete your account? This action cannot be undone.
              </p>
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  className="bg-red-500 hover:bg-red-600"
                  onClick={() => {
                    // TODO: Implement account deletion
                    console.log("Account deletion not implemented yet");
                  }}
                >
                  Yes, Delete My Account
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
