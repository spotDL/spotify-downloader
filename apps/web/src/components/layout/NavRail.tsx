import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { Download, Flag, Home, Library, Settings, User } from "lucide-react";
import { useMe } from "../../api/queries";
import { useFeature } from "../../app/config";
import { cn } from "../../lib/utils";

// The primary navigation: a grouped sidebar on desktop (Discover / Library /
// System) with a meter-bar wordmark, reflowing to a fixed bottom bar on mobile.
// One `<nav aria-label="Primary">` (never duplicated — the shell contract
// asserts a single Primary nav with uniquely-named links). Active state is
// amber, driven by TanStack Router's `data-status`. Feature gating and links
// are unchanged from the icon rail; only the visuals/grouping differ.

const RAIL_LINK =
  "flex items-center gap-3 rounded-md text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground data-[status=active]:bg-elevated data-[status=active]:text-primary max-sm:size-11 max-sm:justify-center sm:px-2.5 sm:py-2";

// The meter-bar wordmark: three amber cells + spotDL in the display face.
function Wordmark() {
  return (
    <Link
      to="/"
      aria-label="spotDL home"
      className="mb-2 hidden items-center gap-2.5 px-2.5 py-1 sm:flex"
    >
      <span
        aria-hidden
        className="flex size-8 items-end justify-center gap-[3px] rounded-md bg-primary p-[7px]"
      >
        <span className="h-2/5 w-[3px] rounded-[1px] bg-primary-foreground/80" />
        <span className="h-full w-[3px] rounded-[1px] bg-primary-foreground" />
        <span className="h-3/5 w-[3px] rounded-[1px] bg-primary-foreground/80" />
      </span>
      <span className="font-display text-lg font-bold tracking-tight">
        spot<span className="text-primary">DL</span>
      </span>
    </Link>
  );
}

function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="hidden px-2.5 pb-1 pt-3 text-xs font-medium uppercase tracking-wider text-faint sm:block">
      {children}
    </p>
  );
}

function RailLink({ to, label, icon }: { to: string; label: string; icon: ReactNode }) {
  return (
    <Link to={to} aria-label={label} title={label} className={RAIL_LINK}>
      {icon}
      <span className="hidden text-sm font-medium sm:inline">{label}</span>
    </Link>
  );
}

function accountInitials(source: string): string {
  const parts = source.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function AccountSlot() {
  const me = useMe();
  if (me.data) {
    const name = me.data.display_name ?? me.data.email;
    return (
      <Link
        to="/settings"
        aria-label="Account"
        title={name}
        className={cn(RAIL_LINK, "sm:gap-2.5")}
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-elevated font-mono text-xs font-semibold text-primary">
          {accountInitials(name)}
        </span>
        <span className="hidden min-w-0 flex-1 truncate text-sm font-medium sm:inline">{name}</span>
      </Link>
    );
  }
  return <RailLink to="/login" label="Sign in" icon={<User className="size-5 shrink-0" />} />;
}

// Admin is a privileged surface — the item appears only once `me` confirms
// is_admin (the /admin route re-checks the same flag in its guard).
function AdminRailLink() {
  const me = useMe();
  if (!me.data?.is_admin) return null;
  return <RailLink to="/admin" label="Admin" icon={<Flag className="size-5 shrink-0" />} />;
}

export function NavRail() {
  const hasDownloads = useFeature("downloads");
  const hasLibrary = useFeature("library");
  const hasAuth = useFeature("auth");
  const showLibraryGroup = hasDownloads || hasLibrary;

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-30 flex h-16 flex-row items-center justify-around border-t border-border bg-surface px-2 sm:sticky sm:inset-x-auto sm:top-0 sm:bottom-auto sm:h-svh sm:w-60 sm:flex-col sm:items-stretch sm:justify-start sm:gap-0.5 sm:overflow-y-auto sm:border-t-0 sm:border-r sm:px-3 sm:py-4"
    >
      <Wordmark />

      <Eyebrow>Discover</Eyebrow>
      <RailLink to="/" label="Home" icon={<Home className="size-5 shrink-0" />} />

      {showLibraryGroup ? <Eyebrow>Library</Eyebrow> : null}
      {hasDownloads ? (
        <RailLink to="/downloads" label="Downloads" icon={<Download className="size-5 shrink-0" />} />
      ) : null}
      {hasLibrary ? (
        <RailLink to="/library" label="Library" icon={<Library className="size-5 shrink-0" />} />
      ) : null}

      <Eyebrow>System</Eyebrow>
      <RailLink to="/settings" label="Settings" icon={<Settings className="size-5 shrink-0" />} />
      {hasAuth ? <AdminRailLink /> : null}

      {hasAuth ? (
        <div className="sm:mt-auto sm:pt-2">
          <AccountSlot />
        </div>
      ) : null}
    </nav>
  );
}
