import { useState, useEffect } from "react";
import { Link, useLocation } from "@tanstack/react-router";
import { clsx } from "clsx";
import { useAuthStore } from "@/stores/auth";
import { features, config } from "@/config";

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

const MatchingIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
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

export interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  adminOnly?: boolean;
}

export interface SidebarProps {
  onSearchClick?: () => void;
  queueCount?: number;
}

export function Sidebar({ onSearchClick, queueCount = 0 }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const location = useLocation();
  const { user } = useAuthStore();

  // Close mobile sidebar on route change
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  const navItems: NavItem[] = [
    { to: "/", label: "Home", icon: <HomeIcon /> },
    ...(features.hasQueue
      ? [{ to: "/queue", label: "Queue", icon: <QueueIcon />, badge: queueCount > 0 ? queueCount : undefined }]
      : []),
    { to: "/matching", label: "Matching", icon: <MatchingIcon /> },
    { to: "/settings", label: "Settings", icon: <SettingsIcon /> },
    { to: "/admin", label: "Admin", icon: <AdminIcon />, adminOnly: true },
  ];

  const filteredNavItems = navItems.filter(
    (item) => !item.adminOnly || (item.adminOnly && user?.is_admin)
  );

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

        {/* Version footer */}
        <div className="p-3 border-t border-[var(--color-border-subtle)]">
          <span
            className={clsx(
              "text-xs text-[var(--color-text-dim)] transition-opacity duration-200",
              isExpanded || isMobileOpen ? "opacity-100" : "opacity-0"
            )}
          >
            v{config.version}
          </span>
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
