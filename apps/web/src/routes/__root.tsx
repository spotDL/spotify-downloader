import { useEffect, useState } from "react";
import {
  createRootRouteWithContext,
  Link,
  Outlet,
} from "@tanstack/react-router";
import type { RouterContext } from "../app/router";
import { EmptyState } from "../components/EmptyState";
import { Toasts } from "../components/Toasts";
import { NavRail } from "../components/layout/NavRail";
import { TopBar } from "../components/layout/TopBar";
import { CommandPalette } from "../components/layout/CommandPalette";

// The root route carries the typed router context (CONTRACT G) so later tasks'
// `beforeLoad` guards read `config`/`auth` synchronously.
export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  notFoundComponent: NotFound,
});

function RootLayout() {
  const [paletteOpen, setPaletteOpen] = useState(false);

  // ⌘K / Ctrl+K toggles the command palette from anywhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex min-h-svh bg-void text-fg">
      <NavRail />
      <div className="flex min-w-0 flex-1 flex-col pb-16 sm:pb-0">
        <TopBar onOpenSearch={() => setPaletteOpen(true)} />
        <main className="animate-fade-in flex-1">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <Toasts />
    </div>
  );
}

function NotFound() {
  return (
    <div className="mx-auto w-full max-w-2xl px-6 py-16">
      <EmptyState
        title="Page not found"
        description="The page you're looking for doesn't exist."
        action={
          <Link
            to="/"
            className="rounded-md px-3 py-1.5 text-sm font-medium text-emerald hover:underline"
          >
            Back to home
          </Link>
        }
      />
    </div>
  );
}
