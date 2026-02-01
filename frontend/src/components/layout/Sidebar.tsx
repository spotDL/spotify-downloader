import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import { clsx } from "clsx";
import { useAuthStore } from "@/stores/auth";
import { useLogout } from "@/api/auth";
import { useDevConfig } from "@/contexts/DevConfigContext";
import { config } from "@/config";

// Icons
const HomeIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const QueueIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const SettingsIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const AdminIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const UserIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const LogoutIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

const ChevronIcon = ({ className }: { className?: string }) => (
  <svg className={clsx("w-4 h-4", className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const LoginIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
  </svg>
);

export interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  adminOnly?: boolean;
  requiresAuth?: boolean;
}

export interface SidebarProps {
  onSearchClick?: () => void;
  queueCount?: number;
}

export function Sidebar({ onSearchClick, queueCount = 0 }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();
  const logoutMutation = useLogout();

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close mobile sidebar and user menu on route change
  useEffect(() => {
    setIsMobileOpen(false);
    setIsUserMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
    navigate({ to: "/auth/login" });
  };

  // Get user initials for avatar
  const getUserInitials = (username: string) => {
    return username.slice(0, 2).toUpperCase();
  };

  const navItems: NavItem[] = [
    { to: "/", label: "Home", icon: <HomeIcon /> },
    ...(features.hasQueue
      ? [{ to: "/queue", label: "Queue", icon: <QueueIcon />, badge: queueCount > 0 ? queueCount : undefined }]
      : []),
    { to: "/settings", label: "Settings", icon: <SettingsIcon />, requiresAuth: true },
    { to: "/admin", label: "Admin", icon: <AdminIcon />, adminOnly: true },
  ];

  const filteredNavItems = navItems.filter((item) => {
    // Hide admin-only items if not admin
    if (item.adminOnly && !user?.is_admin) return false;
    // Hide auth-required items if not authenticated
    if (item.requiresAuth && !isAuthenticated) return false;
    return true;
  });

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed left-0 top-0 bottom-0 z-50",
          "bg-[var(--bg-panel)] border-r border-[var(--color-border-subtle)]",
          "flex flex-col",
          "transition-all duration-200",
          // Desktop: collapsed by default, expands on hover
          "md:w-16 md:hover:w-56",
          // Mobile: hidden by default, full width when open
          "w-64",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
        onMouseEnter={() => setIsExpanded(true)}
        onMouseLeave={() => setIsExpanded(false)}
      >
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-[var(--color-border-subtle)]">
          <Link to="/" className="flex items-center gap-3">
            <div className="relative w-8 h-8 flex-shrink-0">
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-900" />
              <div className="absolute inset-[6px] rounded-full bg-gradient-to-br from-[var(--accent-safe)] to-[var(--accent-cool)] flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-900" />
              </div>
            </div>
            <span
              className={clsx(
                "font-bold text-lg whitespace-nowrap transition-opacity duration-200",
                isExpanded || isMobileOpen ? "opacity-100" : "opacity-0 md:group-hover:opacity-100"
              )}
            >
              <span className="text-[var(--accent-safe)]">spot</span>
              <span className="text-zinc-100">DL</span>
            </span>
          </Link>
        </div>

        {/* Search button */}
        <div className="p-3">
          <button
            onClick={onSearchClick}
            className={clsx(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg",
              "bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)]",
              "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
              "transition-colors"
            )}
          >
            <SearchIcon />
            <span
              className={clsx(
                "flex-1 text-left text-sm whitespace-nowrap transition-opacity duration-200",
                isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
              )}
            >
              Search...
            </span>
            <kbd
              className={clsx(
                "px-1.5 py-0.5 text-xs rounded bg-[var(--bg-hover)] text-[var(--color-text-dim)] transition-opacity duration-200",
                isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
              )}
            >
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {filteredNavItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg",
                "transition-colors",
                isActive(item.to)
                  ? "bg-[var(--accent-safe)]/10 text-[var(--accent-safe)]"
                  : "text-[var(--color-text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--color-text-primary)]"
              )}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              <span
                className={clsx(
                  "flex-1 text-sm font-medium whitespace-nowrap transition-opacity duration-200",
                  isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
                )}
              >
                {item.label}
              </span>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={clsx(
                    "flex-shrink-0 min-w-[20px] h-5 px-1.5 rounded-full",
                    "bg-[var(--accent-needle)] text-white",
                    "text-xs font-semibold flex items-center justify-center",
                    "transition-opacity duration-200",
                    isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
                  )}
                >
                  {item.badge > 99 ? "99+" : item.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-[var(--color-border-subtle)]" ref={userMenuRef}>
          {isAuthenticated && user ? (
            <div className="relative">
              {/* User menu trigger */}
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className={clsx(
                  "w-full flex items-center gap-3 p-3",
                  "hover:bg-[var(--bg-hover)] transition-colors",
                  isUserMenuOpen && "bg-[var(--bg-hover)]"
                )}
              >
                {/* Avatar */}
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--accent-safe)] to-[var(--accent-cool)] flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-semibold text-white">
                    {getUserInitials(user.username)}
                  </span>
                </div>
                {/* User info */}
                <div
                  className={clsx(
                    "flex-1 min-w-0 text-left transition-opacity duration-200",
                    isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
                  )}
                >
                  <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                    {user.username}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)] truncate">
                    {user.email}
                  </p>
                </div>
                {/* Chevron */}
                <ChevronIcon
                  className={clsx(
                    "text-[var(--color-text-muted)] transition-all duration-200",
                    isExpanded || isMobileOpen ? "opacity-100" : "opacity-0",
                    isUserMenuOpen && "rotate-180"
                  )}
                />
              </button>

              {/* Dropdown menu */}
              {isUserMenuOpen && (isExpanded || isMobileOpen) && (
                <div className="absolute bottom-full left-0 right-0 mb-1 mx-2 py-1 bg-[var(--bg-surface)] border border-[var(--color-border-subtle)] rounded-lg shadow-lg overflow-hidden">
                  <Link
                    to="/account"
                    className="flex items-center gap-3 px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--color-text-primary)] transition-colors"
                  >
                    <UserIcon />
                    <span>Account Settings</span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    disabled={logoutMutation.isPending}
                    className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--bg-hover)] hover:text-red-400 transition-colors disabled:opacity-50"
                  >
                    <LogoutIcon />
                    <span>{logoutMutation.isPending ? "Logging out..." : "Log Out"}</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link
              to="/auth/login"
              className={clsx(
                "flex items-center gap-3 p-3",
                "text-[var(--color-text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--color-text-primary)]",
                "transition-colors"
              )}
            >
              <div className="w-8 h-8 rounded-full bg-[var(--bg-surface)] border border-[var(--color-border-subtle)] flex items-center justify-center flex-shrink-0">
                <LoginIcon />
              </div>
              <span
                className={clsx(
                  "text-sm font-medium transition-opacity duration-200",
                  isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
                )}
              >
                Sign In
              </span>
            </Link>
          )}

          {/* Version - compact */}
          <div className="px-3 pb-2 pt-1">
            <span
              className={clsx(
                "text-[10px] text-[var(--color-text-dim)] transition-opacity duration-200",
                isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
              )}
            >
              v{config.version}
            </span>
          </div>
        </div>
      </aside>

      {/* Mobile menu button - fixed at bottom right */}
      <button
        onClick={() => setIsMobileOpen(true)}
        className={clsx(
          "fixed bottom-6 left-6 z-40 md:hidden",
          "w-14 h-14 rounded-full",
          "bg-[var(--accent-safe)] text-white",
          "shadow-lg shadow-[var(--accent-safe)]/30",
          "flex items-center justify-center",
          "active:scale-95 transition-transform"
        )}
      >
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile close button when sidebar is open */}
      {isMobileOpen && (
        <button
          onClick={() => setIsMobileOpen(false)}
          className="fixed top-4 right-4 z-50 md:hidden w-10 h-10 rounded-full bg-zinc-800 text-zinc-400 flex items-center justify-center"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </>
  );
}

export default Sidebar;
