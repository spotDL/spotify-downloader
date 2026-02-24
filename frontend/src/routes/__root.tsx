import { createRootRoute, Outlet, useLocation } from "@tanstack/react-router";
import { useEffect } from "react";
import { clsx } from "clsx";
import { ToastProvider } from "@/components/ui/toast";
import {
  Sidebar,
  Breadcrumb,
  CommandPalette,
  useCommandPalette,
  buildBreadcrumbsFromPath,
} from "@/components/layout";
import { DevModePanel } from "@/components/dev";
import { DevConfigProvider, useDevConfig } from "@/contexts/DevConfigContext";
import { useSettingsStore } from "@/stores/settings";
import { config } from "@/config";

export const Route = createRootRoute({
  component: RootLayout,
});

// Top bar component
function TopBar({
  onSearchClick,
  breadcrumbs,
}: {
  onSearchClick: () => void;
  breadcrumbs: { label: string; to?: string }[];
}) {
  return (
    <header className="h-14 bg-[var(--bg-chassis)] border-b border-[var(--color-border-subtle)] flex items-center justify-between px-6">
      {/* Left: Breadcrumb */}
      <div className="flex items-center gap-4">
        <Breadcrumb items={breadcrumbs} />
      </div>

      {/* Right: Search */}
      <div className="flex items-center">
        <button
          onClick={onSearchClick}
          className={clsx(
            "flex items-center gap-3 px-4 py-2 rounded-xl",
            "bg-[var(--bg-surface)] border border-[var(--color-border-subtle)]",
            "text-sm text-[var(--color-text-muted)]",
            "hover:text-[var(--color-text-secondary)] hover:border-[var(--color-border)] hover:bg-[var(--bg-hover)]",
            "transition-colors duration-150",
            "min-w-[200px] sm:min-w-[280px]"
          )}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span className="flex-1 text-left">Search songs, albums, artists...</span>
          <kbd className="hidden sm:inline px-2 py-1 rounded-md bg-[var(--bg-void)] text-xs font-medium">
            ⌘K
          </kbd>
        </button>
      </div>
    </header>
  );
}

function RootLayout() {
  return (
    <DevConfigProvider>
      <RootLayoutContent />
    </DevConfigProvider>
  );
}

function RootLayoutContent() {
  const location = useLocation();
  const { isOpen: isPaletteOpen, open: openPalette, close: closePalette } = useCommandPalette();
  const { features } = useDevConfig();
  const enableAnimations = useSettingsStore((s) => s.enableAnimations);
  const reduceMotion = useSettingsStore((s) => s.reduceMotion);

  // Apply animation settings globally via CSS class on document root
  useEffect(() => {
    const root = document.documentElement;
    if (!enableAnimations || reduceMotion) {
      root.classList.add("reduce-motion");
    } else {
      root.classList.remove("reduce-motion");
    }
  }, [enableAnimations, reduceMotion]);

  // Build breadcrumbs from current path
  const breadcrumbs = buildBreadcrumbsFromPath(location.pathname);

  return (
    <ToastProvider>
      <div className="min-h-screen bg-[var(--bg-void)] text-[var(--color-text-primary)]">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="md:ml-16 flex flex-col min-h-screen">
          {/* Hosted Mode Banner */}
          {features.isHosted && (
            <div className="bg-gradient-to-r from-[var(--accent-needle)]/10 via-[var(--accent-warm)]/10 to-[var(--accent-safe)]/10 border-b border-[var(--accent-needle)]/20 py-2 px-4 text-center">
              <p className="text-sm text-[var(--accent-warm)]">
                Welcome to SpotDL - cross-platform metadata, matching, and downloads.{" "}
                <a
                  href={config.githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium underline underline-offset-2 hover:text-[var(--accent-needle)]"
                >
                  Self-host
                </a>{" "}
                for downloads.
              </p>
            </div>
          )}

          {/* Top bar */}
          <TopBar
            onSearchClick={openPalette}
            breadcrumbs={breadcrumbs}
          />

          {/* Page content */}
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-7xl mx-auto px-6 py-8">
              <div className="animate-fade-in">
                <Outlet />
              </div>
            </div>
          </main>

          {/* Footer */}
          <footer className="border-t border-[var(--color-border-subtle)] py-4 px-6">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <p className="text-xs text-[var(--color-text-dim)]">
                SpotDL v{config.version}
              </p>
              <div className="flex items-center gap-4">
                <a
                  href={config.githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[var(--color-text-dim)] hover:text-[var(--color-text-muted)] transition-colors"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                </a>
              </div>
            </div>
          </footer>
        </div>

        {/* Command Palette */}
        <CommandPalette isOpen={isPaletteOpen} onClose={closePalette} />

        {/* Dev Mode Panel - only visible in development */}
        <DevModePanel />
      </div>
    </ToastProvider>
  );
}
