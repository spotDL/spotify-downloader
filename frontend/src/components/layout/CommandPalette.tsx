import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { createPortal } from "react-dom";
import { clsx } from "clsx";
import { useUniversalSearch } from "@/api";
import type { SearchResult, EntityType } from "@/types";
import { Spinner } from "@/components/ui";

// Icons
const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const EntityIcons: Record<EntityType, React.ReactNode> = {
  artist: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  ),
  album: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
  playlist: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  ),
  track: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
    </svg>
  ),
  all: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
};

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Search query
  const { data: searchData, isLoading } = useUniversalSearch(
    { query, limit: 8 },
    { enabled: query.length >= 2 }
  );

  const results = searchData?.results ?? [];

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (results[selectedIndex]) {
            handleSelect(results[selectedIndex]);
          } else if (query.length > 0) {
            // Navigate to search page with query
            navigate({ to: "/search", search: { q: query } });
            onClose();
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [results, selectedIndex, query, navigate, onClose]
  );

  // Handle result selection
  const handleSelect = (result: SearchResult) => {
    const routes: Record<EntityType, string> = {
      artist: `/artist/${result.id}`,
      album: `/album/${result.id}`,
      playlist: `/playlist/${result.id}`,
      track: `/song/${result.id}`,
      all: `/search`,
    };

    navigate({ to: routes[result.entity_type] ?? "/search" });
    onClose();
  };

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Global keyboard shortcut
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        }
      }
    };

    document.addEventListener("keydown", handleGlobalKeyDown);
    return () => document.removeEventListener("keydown", handleGlobalKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="command-palette-backdrop fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4 md:pl-20"
      onClick={handleBackdropClick}
      style={{ backgroundColor: "rgba(0, 0, 0, 0.5)" }}
    >
      <div
        className={clsx(
          "command-palette w-full max-w-xl mx-auto",
          "bg-[var(--bg-panel)] border border-[var(--color-border)]",
          "rounded-2xl shadow-2xl",
          "animate-scale-in overflow-hidden"
        )}
        role="combobox"
        aria-expanded={results.length > 0}
        aria-haspopup="listbox"
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-[var(--color-border-subtle)]">
          <SearchIcon />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search artists, albums, songs..."
            className={clsx(
              "command-palette-input flex-1 bg-transparent border-none",
              "text-lg text-[var(--color-text-primary)]",
              "placeholder:text-[var(--color-text-muted)]",
              "focus:outline-none"
            )}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck="false"
          />
          {isLoading && <Spinner size="sm" />}
          <kbd className="px-2 py-1 text-xs rounded-lg bg-[var(--bg-surface)] text-[var(--color-text-dim)]">
            ESC
          </kbd>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <ul
            className="max-h-[400px] overflow-y-auto py-2"
            role="listbox"
          >
            {results.map((result, index) => (
              <li
                key={result.id}
                role="option"
                aria-selected={index === selectedIndex}
                className={clsx(
                  "flex items-center gap-3 px-4 py-3 cursor-pointer",
                  "transition-colors duration-100",
                  index === selectedIndex
                    ? "bg-[var(--accent-safe)]/10"
                    : "hover:bg-[var(--bg-hover)]"
                )}
                onClick={() => handleSelect(result)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                {/* Image */}
                <div
                  className={clsx(
                    "w-10 h-10 flex-shrink-0 overflow-hidden",
                    "bg-[var(--bg-surface)]",
                    result.entity_type === "artist" ? "rounded-full" : "rounded-lg"
                  )}
                >
                  {result.image_url ? (
                    <img
                      src={result.image_url}
                      alt={result.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[var(--color-text-dim)]">
                      {EntityIcons[result.entity_type]}
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                    {result.name}
                  </p>
                  {result.subtitle && (
                    <p className="text-xs text-[var(--color-text-muted)] truncate">
                      {result.subtitle}
                    </p>
                  )}
                </div>

                {/* Type badge */}
                <span
                  className={clsx(
                    "px-2 py-0.5 rounded-full text-xs font-medium capitalize",
                    "bg-[var(--bg-surface)] text-[var(--color-text-muted)]"
                  )}
                >
                  {result.entity_type}
                </span>
              </li>
            ))}
          </ul>
        )}

        {/* Empty state */}
        {query.length >= 2 && !isLoading && results.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-[var(--color-text-muted)]">
              No results found for "{query}"
            </p>
            <p className="text-sm text-[var(--color-text-dim)] mt-1">
              Try searching for an artist, album, or song
            </p>
          </div>
        )}

        {/* Initial state */}
        {query.length < 2 && (
          <div className="px-4 py-6 text-center">
            <p className="text-sm text-[var(--color-text-muted)]">
              Type at least 2 characters to search
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border-subtle)] bg-[var(--bg-elevated)]">
          <div className="flex items-center gap-4 text-xs text-[var(--color-text-dim)]">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--bg-surface)]">↑↓</kbd>
              Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--bg-surface)]">↵</kbd>
              Select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--bg-surface)]">ESC</kbd>
              Close
            </span>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}

/**
 * Hook to manage command palette state
 */
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  };
}

export default CommandPalette;
