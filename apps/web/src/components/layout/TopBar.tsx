import { Monitor, Moon, Search, Sun } from "lucide-react";
import { useUiStore } from "../../stores/ui";
import { Kbd } from "../ui/kbd";

// The sticky top bar: a ⌘K search trigger (opens the command palette; the
// shortcut itself is bound in the shell) and a theme toggle cycling
// dark → light → system via the ui store.

function ThemeToggle() {
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const next = theme === "dark" ? "light" : theme === "light" ? "system" : "dark";
  const Icon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      aria-label={`Theme: ${theme}. Switch to ${next}.`}
      className="flex size-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground"
    >
      <Icon className="size-4" />
    </button>
  );
}

export function TopBar({ onOpenSearch }: { onOpenSearch: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-md sm:px-6">
      <button
        type="button"
        onClick={onOpenSearch}
        aria-label="Search"
        aria-keyshortcuts="Meta+K Control+K"
        className="flex h-9 w-full max-w-sm items-center gap-2.5 rounded-md border border-border bg-surface px-3 text-sm text-muted-foreground transition-colors hover:border-faint/60 hover:text-foreground"
      >
        <Search className="size-4 shrink-0" />
        <span className="truncate">Search songs, albums, artists</span>
        <Kbd className="ml-auto">⌘K</Kbd>
      </button>
      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  );
}
