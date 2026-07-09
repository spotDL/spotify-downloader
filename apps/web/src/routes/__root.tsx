import { useState } from "react";
import {
  createRootRouteWithContext,
  Link,
  Outlet,
  useNavigate,
} from "@tanstack/react-router";
import type { RouterContext } from "../app/router";
import { useUiStore } from "../stores/ui";
import { Feature } from "../components/Feature";
import { Input } from "../components/Input";
import { EmptyState } from "../components/EmptyState";
import { Toasts } from "../components/Toasts";

// The root route carries the typed router context (CONTRACT G) so later tasks'
// `beforeLoad` guards read `config`/`auth` synchronously.
export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  notFoundComponent: NotFound,
});

const NAV_LINK_CLASS =
  "rounded-md px-2.5 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-black/5 hover:text-fg data-[status=active]:bg-brand-100 data-[status=active]:text-brand-700 dark:hover:bg-white/10 dark:data-[status=active]:bg-brand-700/30 dark:data-[status=active]:text-brand-100";

function ThemeToggle() {
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      aria-label={`Switch to ${isDark ? "light" : "dark"} theme`}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="rounded-md px-2.5 py-1.5 text-sm text-muted hover:bg-black/5 hover:text-fg dark:hover:bg-white/10"
    >
      {isDark ? "Light" : "Dark"}
    </button>
  );
}

function NavSearch() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  return (
    <form
      role="search"
      className="min-w-0 flex-1 sm:max-w-xs"
      onSubmit={(e) => {
        e.preventDefault();
        const query = q.trim();
        if (query.length > 0) {
          void navigate({ to: "/", search: { q: query } });
        }
      }}
    >
      <Input
        type="search"
        aria-label="Search"
        placeholder="Search tracks, albums, artists…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
    </form>
  );
}

function RootLayout() {
  return (
    <div className="flex min-h-svh flex-col bg-bg text-fg">
      <header className="border-b border-black/10 bg-surface dark:border-white/10">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <Link to="/" className="text-lg font-semibold text-fg">
            spotDL
          </Link>
          <NavSearch />
          <nav className="flex items-center gap-1" aria-label="Primary">
            <Link to="/" className={NAV_LINK_CLASS}>
              Home
            </Link>
            <Feature flag="downloads">
              <Link to="/downloads" className={NAV_LINK_CLASS}>
                Downloads
              </Link>
            </Feature>
            <Feature flag="library">
              <Link to="/library" className={NAV_LINK_CLASS}>
                Library
              </Link>
            </Feature>
            <Link to="/settings" className={NAV_LINK_CLASS}>
              Settings
            </Link>
            <Feature flag="auth">
              <Link to="/login" className={NAV_LINK_CLASS}>
                Sign in
              </Link>
            </Feature>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <Toasts />
    </div>
  );
}

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you're looking for doesn't exist."
      action={
        <Link to="/" className={NAV_LINK_CLASS}>
          Back to home
        </Link>
      }
    />
  );
}
