import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { useMe } from "../../api/queries";
import { Feature } from "../Feature";
import {
  DownloadIcon,
  FlagIcon,
  LibraryIcon,
  SearchIcon,
  SettingsIcon,
  UserIcon,
} from "../icons";

// The left icon rail (mockup `.rail`): logo, the feature-gated primary links,
// and a bottom account slot. One `<nav aria-label="Primary">` reflows to a
// fixed bottom bar on mobile (never duplicated — the shell contract asserts a
// single Primary nav with uniquely-named links). Active = emerald, driven by
// TanStack Router's `data-status`.

const ITEM =
  "relative grid size-11 place-items-center rounded-xl text-muted transition-colors hover:bg-hover hover:text-ink-2 data-[status=active]:bg-emerald/10 data-[status=active]:text-emerald";

function RailLink({
  to,
  label,
  children,
}: {
  to: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <Link to={to} aria-label={label} title={label} className={ITEM}>
      {children}
    </Link>
  );
}

function AccountSlot() {
  const me = useMe();
  if (me.data) {
    const initials = accountInitials(me.data.display_name ?? me.data.email);
    return (
      <Link
        to="/settings"
        aria-label="Account"
        title={me.data.display_name ?? me.data.email}
        className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-emerald to-teal text-[13px] font-bold text-void"
      >
        {initials}
      </Link>
    );
  }
  return (
    <RailLink to="/login" label="Sign in">
      <UserIcon className="size-5" />
    </RailLink>
  );
}

// Admin is a privileged surface — the rail item appears only once ["me"]
// confirms is_admin (the /admin route re-checks the same flag in its guard).
function AdminRailLink() {
  const me = useMe();
  if (!me.data?.is_admin) return null;
  return (
    <RailLink to="/admin" label="Admin">
      <FlagIcon className="size-5" />
    </RailLink>
  );
}

function accountInitials(source: string): string {
  const parts = source.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function NavRail() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-30 flex h-16 flex-row items-center justify-around border-t border-line-soft bg-panel px-2 sm:sticky sm:inset-x-auto sm:top-0 sm:bottom-auto sm:h-svh sm:w-[76px] sm:flex-col sm:justify-start sm:gap-1.5 sm:border-t-0 sm:border-r sm:px-0 sm:py-3.5"
    >
      <span
        aria-hidden
        className="mb-5 hidden size-10 rounded-full shadow-[0_0_22px_-4px_var(--color-emerald)] sm:block"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, #0f1012 26%, transparent 27%), conic-gradient(from 200deg, #00d084, #4ecdc4, #00d084)",
        }}
      />
      <RailLink to="/" label="Home">
        <SearchIcon className="size-5" />
      </RailLink>
      <Feature flag="downloads">
        <RailLink to="/downloads" label="Downloads">
          <DownloadIcon className="size-5" />
        </RailLink>
      </Feature>
      <Feature flag="library">
        <RailLink to="/library" label="Library">
          <LibraryIcon className="size-5" />
        </RailLink>
      </Feature>
      <RailLink to="/settings" label="Settings">
        <SettingsIcon className="size-5" />
      </RailLink>
      <Feature flag="auth">
        <AdminRailLink />
      </Feature>
      <div className="sm:mt-auto">
        <Feature flag="auth">
          <AccountSlot />
        </Feature>
      </div>
    </nav>
  );
}
