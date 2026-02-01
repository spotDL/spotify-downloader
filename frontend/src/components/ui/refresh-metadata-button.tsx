import { useState, useRef } from "react";
import { clsx } from "clsx";
import { Button } from "./button";

interface RefreshMetadataButtonProps {
  onRefresh: () => Promise<void>;
  onEnrich?: () => Promise<void>;
  className?: string;
  variant?: "default" | "ghost" | "icon";
  size?: "sm" | "md" | "lg";
  showEnrichOption?: boolean;
}

/**
 * Button to refresh metadata for an entity from its source platform.
 * Optionally supports enrichment from external metadata sources.
 * Shows loading state and success/error feedback.
 */
export function RefreshMetadataButton({
  onRefresh,
  onEnrich,
  className,
  variant = "ghost",
  size = "sm",
  showEnrichOption = false,
}: RefreshMetadataButtonProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);
  const [feedback, setFeedback] = useState<"success" | "error" | "enriched" | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setFeedback(null);
    setShowMenu(false);

    try {
      await onRefresh();
      setFeedback("success");
      // Clear success feedback after 2 seconds
      setTimeout(() => setFeedback(null), 2000);
    } catch {
      setFeedback("error");
      // Clear error feedback after 3 seconds
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleEnrich = async () => {
    if (!onEnrich) return;

    setIsEnriching(true);
    setFeedback(null);
    setShowMenu(false);

    try {
      await onEnrich();
      setFeedback("enriched");
      // Clear success feedback after 2 seconds
      setTimeout(() => setFeedback(null), 2000);
    } catch {
      setFeedback("error");
      // Clear error feedback after 3 seconds
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      setIsEnriching(false);
    }
  };

  const handleRefreshWithEnrich = async () => {
    setIsRefreshing(true);
    setFeedback(null);

    try {
      // Refresh first
      await onRefresh();

      // Then enrich if available
      if (onEnrich) {
        setIsEnriching(true);
        await onEnrich();
      }

      setFeedback("enriched");
      setTimeout(() => setFeedback(null), 2000);
    } catch {
      setFeedback("error");
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      setIsRefreshing(false);
      setIsEnriching(false);
    }
  };

  const isLoading = isRefreshing || isEnriching;

  // Close menu when clicking outside
  const handleClickOutside = (e: React.MouseEvent) => {
    if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
      setShowMenu(false);
    }
  };

  if (variant === "icon") {
    return (
      <button
        onClick={handleRefresh}
        disabled={isLoading}
        title="Refresh metadata"
        className={clsx(
          "p-2 rounded-lg transition-all",
          "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          (feedback === "success" || feedback === "enriched") && "text-emerald-400",
          feedback === "error" && "text-red-400",
          className
        )}
      >
        <svg
          className={clsx("w-4 h-4", isLoading && "animate-spin")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          {isLoading ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          ) : feedback === "success" || feedback === "enriched" ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          ) : feedback === "error" ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          )}
        </svg>
      </button>
    );
  }

  // Show dropdown menu if enrich option is enabled
  if (showEnrichOption && onEnrich) {
    return (
      <div className="relative" ref={menuRef}>
        <div className="flex">
          <Button
            variant={variant === "default" ? "primary" : "outline"}
            size={size}
            onClick={handleRefreshWithEnrich}
            disabled={isLoading}
            className={clsx(
              "rounded-r-none border-r-0",
              (feedback === "success" || feedback === "enriched") && "!text-emerald-400",
              feedback === "error" && "!text-red-400",
              className
            )}
          >
            <svg
              className={clsx("w-4 h-4 mr-2", isLoading && "animate-spin")}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {isRefreshing
              ? "Refreshing..."
              : isEnriching
                ? "Enriching..."
                : feedback === "success"
                  ? "Refreshed!"
                  : feedback === "enriched"
                    ? "Enriched!"
                    : feedback === "error"
                      ? "Failed"
                      : "Refresh & Enrich"}
          </Button>
          <Button
            variant={variant === "default" ? "primary" : "outline"}
            size={size}
            onClick={() => setShowMenu(!showMenu)}
            disabled={isLoading}
            className="rounded-l-none px-2"
          >
            <svg
              className={clsx("w-4 h-4 transition-transform", showMenu && "rotate-180")}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </Button>
        </div>

        {/* Dropdown menu */}
        {showMenu && (
          <div
            className="absolute right-0 top-full mt-1 w-48 rounded-lg bg-zinc-800 border border-zinc-700 shadow-lg z-50"
            onClick={handleClickOutside}
          >
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-700 rounded-t-lg transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh Only
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">From source platform</p>
            </button>
            <button
              onClick={handleEnrich}
              disabled={isLoading}
              className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-700 transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                Enrich Only
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">From MusicBrainz, Discogs</p>
            </button>
            <button
              onClick={handleRefreshWithEnrich}
              disabled={isLoading}
              className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-700 rounded-b-lg transition-colors border-t border-zinc-700"
            >
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Refresh + Enrich
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">Full metadata update</p>
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <Button
      variant={variant === "default" ? "primary" : "ghost"}
      size={size}
      onClick={handleRefresh}
      disabled={isLoading}
      className={clsx(
        (feedback === "success" || feedback === "enriched") && "!text-emerald-400",
        feedback === "error" && "!text-red-400",
        className
      )}
    >
      <svg
        className={clsx("w-4 h-4 mr-2", isLoading && "animate-spin")}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
      {isLoading
        ? "Refreshing..."
        : feedback === "success" || feedback === "enriched"
          ? "Refreshed!"
          : feedback === "error"
            ? "Failed"
            : "Refresh"}
    </Button>
  );
}

export default RefreshMetadataButton;
