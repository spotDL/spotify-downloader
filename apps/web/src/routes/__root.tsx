import { useEffect, useState } from "react";
import {
  createRootRouteWithContext,
  Link,
  Outlet,
} from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import type { RouterContext } from "../app/router";
import { EmptyState } from "../components/EmptyState";
import { Toaster } from "../components/ui/sonner";
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
  const reduceMotion = useReducedMotion();

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
    <div className="flex min-h-svh bg-background text-foreground">
      {/* Mounted before the Outlet so sonner's store subscription is live before
          any route mount-effect emits a toast (e.g. the OAuth callback, which
          toasts an error and navigates away in the same tick). */}
      <Toaster />
      <NavRail />
      <div className="flex min-w-0 flex-1 flex-col pb-16 sm:pb-0">
        <TopBar onOpenSearch={() => setPaletteOpen(true)} />
        <main className="flex-1">
          <motion.div
            key={reduceMotion ? "static" : undefined}
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto w-full max-w-6xl px-6 py-8"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you're looking for doesn't exist."
      action={
        <Link
          to="/"
          className="rounded-md px-3 py-1.5 text-sm font-medium text-primary hover:underline"
        >
          Back to home
        </Link>
      }
    />
  );
}
