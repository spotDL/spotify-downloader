import { useRouterState } from "@tanstack/react-router";
import { ChevronRightIcon, SearchIcon } from "../icons";

// The sticky top bar (mockup `.topbar`): a breadcrumb on the left and the ⌘K
// search-trigger on the right. The trigger opens the command palette; the ⌘K
// shortcut itself is bound in the shell.

const SEGMENT_LABEL: Record<string, string> = {
  search: "Search",
  tracks: "Track",
  albums: "Album",
  artists: "Artist",
  playlists: "Playlist",
  downloads: "Queue",
  library: "Library",
  settings: "Settings",
  admin: "Admin",
  login: "Sign in",
  register: "Register",
};

function useCrumb(): string | null {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const first = pathname.split("/").filter(Boolean)[0];
  if (!first) return null;
  return SEGMENT_LABEL[first] ?? null;
}

export function TopBar({ onOpenSearch }: { onOpenSearch: () => void }) {
  const crumb = useCrumb();
  return (
    <div className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-line-soft bg-chassis/80 px-5 backdrop-blur-md">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px]">
        <span className="text-muted">spotDL</span>
        {crumb ? (
          <>
            <ChevronRightIcon className="size-3.5 text-ink-4" />
            <span className="text-fg">{crumb}</span>
          </>
        ) : null}
      </nav>
      <button
        type="button"
        onClick={onOpenSearch}
        aria-label="Search"
        aria-keyshortcuts="Meta+K Control+K"
        className="ml-auto flex h-9 min-w-[240px] items-center gap-2.5 rounded-[10px] border border-line bg-surface px-3 text-[13px] text-muted transition-colors hover:border-line hover:bg-hover"
      >
        <SearchIcon className="size-4" />
        <span className="hidden sm:inline">Search songs, albums, artists…</span>
        <span className="sm:hidden">Search…</span>
        <kbd className="ml-auto rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-muted">
          ⌘K
        </kbd>
      </button>
    </div>
  );
}
