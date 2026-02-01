import { useState, useEffect, useRef, useMemo } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Lyrics, LyricsLine, ParsedLyrics, LyricsSource } from "@/types";
import { Spinner } from "@/components/ui";

// Source icons/badges
const sourceLabels: Record<LyricsSource, string> = {
  genius: "Genius",
  musixmatch: "MusixMatch",
  azlyrics: "AZLyrics",
  synced: "Synced",
};

const sourceColors: Record<LyricsSource, string> = {
  genius: "#ffff64",
  musixmatch: "#ff0066",
  azlyrics: "#2b77bf",
  synced: "var(--accent-safe)",
};

// Icons
const CopyIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const ExpandIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
  </svg>
);

const CollapseIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
  </svg>
);

/**
 * Parse LRC format to structured lyrics lines
 */
function parseLRC(lrc: string): LyricsLine[] {
  const lines: LyricsLine[] = [];
  const lrcLines = lrc.split("\n");

  for (const line of lrcLines) {
    // Match timestamp pattern [mm:ss.xx] or [mm:ss]
    const match = line.match(/^\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)$/);
    if (match) {
      const minutes = parseInt(match[1], 10);
      const seconds = parseInt(match[2], 10);
      const hundredths = match[3] ? parseInt(match[3], 10) : 0;
      const text = match[4].trim();

      // Convert to milliseconds
      const timestamp = (minutes * 60 + seconds) * 1000 + hundredths * 10;

      if (text) {
        lines.push({ timestamp, text });
      }
    }
  }

  return lines.sort((a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0));
}

/**
 * Parse plain text lyrics to structured format
 */
function parsePlainLyrics(text: string): LyricsLine[] {
  return text
    .split("\n")
    .map((line) => ({ timestamp: null, text: line.trim() }))
    .filter((line) => line.text.length > 0);
}

export interface LyricsDisplayProps {
  /** Lyrics data */
  lyrics: Lyrics | null;
  /** Loading state */
  isLoading?: boolean;
  /** Error message */
  error?: string | null;
  /** Current playback time in milliseconds (for synced lyrics) */
  currentTime?: number;
  /** Callback when a synced line is clicked */
  onSeek?: (timestamp: number) => void;
  /** Whether to auto-scroll to current line */
  autoScroll?: boolean;
  /** Maximum height before requiring scroll */
  maxHeight?: string;
  /** Additional class names */
  className?: string;
}

export function LyricsDisplay({
  lyrics,
  isLoading = false,
  error = null,
  currentTime = 0,
  onSeek,
  autoScroll = true,
  maxHeight = "400px",
  className,
}: LyricsDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const activeLineRef = useRef<HTMLDivElement>(null);

  // Parse lyrics
  const parsedLyrics: ParsedLyrics | null = useMemo(() => {
    if (!lyrics) return null;

    if (lyrics.lyrics_synced) {
      const lines = parseLRC(lyrics.lyrics_synced);
      if (lines.length > 0) {
        return { lines, isSynced: true, source: lyrics.source };
      }
    }

    const lines = parsePlainLyrics(lyrics.lyrics_text);
    return { lines, isSynced: false, source: lyrics.source };
  }, [lyrics]);

  // Find current line index for synced lyrics
  const currentLineIndex = useMemo(() => {
    if (!parsedLyrics?.isSynced) return -1;

    let index = -1;
    for (let i = 0; i < parsedLyrics.lines.length; i++) {
      const timestamp = parsedLyrics.lines[i].timestamp;
      if (timestamp !== null && timestamp <= currentTime) {
        index = i;
      } else {
        break;
      }
    }
    return index;
  }, [parsedLyrics, currentTime]);

  // Auto-scroll to current line
  useEffect(() => {
    if (autoScroll && activeLineRef.current && containerRef.current) {
      const container = containerRef.current;
      const activeLine = activeLineRef.current;

      const containerRect = container.getBoundingClientRect();
      const lineRect = activeLine.getBoundingClientRect();

      const isVisible =
        lineRect.top >= containerRect.top &&
        lineRect.bottom <= containerRect.bottom;

      if (!isVisible) {
        activeLine.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [currentLineIndex, autoScroll]);

  // Copy lyrics to clipboard
  const handleCopy = async () => {
    if (!parsedLyrics) return;

    const text = parsedLyrics.lines.map((l) => l.text).join("\n");
    await navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  // Format timestamp
  const formatTimestamp = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        className={twMerge(
          clsx(
            "flex flex-col items-center justify-center py-12",
            "bg-[var(--bg-panel)] rounded-2xl border border-[var(--color-border-subtle)]"
          ),
          className
        )}
      >
        <Spinner size="lg" />
        <p className="mt-4 text-[var(--color-text-muted)]">Loading lyrics...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={twMerge(
          clsx(
            "flex flex-col items-center justify-center py-12",
            "bg-[var(--bg-panel)] rounded-2xl border border-[var(--color-border-subtle)]"
          ),
          className
        )}
      >
        <p className="text-[var(--accent-peak)]">{error}</p>
      </div>
    );
  }

  // No lyrics state
  if (!parsedLyrics || parsedLyrics.lines.length === 0) {
    return (
      <div
        className={twMerge(
          clsx(
            "flex flex-col items-center justify-center py-12",
            "bg-[var(--bg-panel)] rounded-2xl border border-[var(--color-border-subtle)]"
          ),
          className
        )}
      >
        <svg
          className="w-12 h-12 text-[var(--color-text-dim)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
          />
        </svg>
        <p className="mt-4 text-[var(--color-text-muted)]">No lyrics available</p>
      </div>
    );
  }

  return (
    <div
      className={twMerge(
        clsx(
          "bg-[var(--bg-panel)] rounded-2xl border border-[var(--color-border-subtle)]",
          "overflow-hidden"
        ),
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border-subtle)]">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
            Lyrics
          </h3>
          <span
            className={clsx(
              "px-2 py-0.5 text-xs font-medium rounded-full",
              "bg-[var(--bg-surface)]"
            )}
            style={{ color: sourceColors[parsedLyrics.source] }}
          >
            {sourceLabels[parsedLyrics.source]}
          </span>
          {parsedLyrics.isSynced && (
            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--accent-safe)]/10 text-[var(--accent-safe)]">
              Synced
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className={clsx(
              "p-2 rounded-lg",
              "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
              "hover:bg-[var(--bg-hover)]",
              "transition-colors duration-150"
            )}
            title="Copy lyrics"
          >
            {isCopied ? (
              <svg className="w-4 h-4 text-[var(--accent-safe)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <CopyIcon />
            )}
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={clsx(
              "p-2 rounded-lg",
              "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
              "hover:bg-[var(--bg-hover)]",
              "transition-colors duration-150"
            )}
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <CollapseIcon /> : <ExpandIcon />}
          </button>
        </div>
      </div>

      {/* Lyrics content */}
      <div
        ref={containerRef}
        className={clsx(
          "lyrics-container px-6 py-4 overflow-y-auto",
          "scrollbar-thin"
        )}
        style={{ maxHeight: isExpanded ? "none" : maxHeight }}
      >
        {parsedLyrics.lines.map((line, index) => {
          const isActive = parsedLyrics.isSynced && index === currentLineIndex;
          const isPast = parsedLyrics.isSynced && index < currentLineIndex;

          return (
            <div
              key={index}
              ref={isActive ? activeLineRef : undefined}
              className={clsx(
                "lyrics-line py-1",
                "transition-all duration-200",
                parsedLyrics.isSynced && "synced cursor-pointer hover:text-[var(--accent-safe)]",
                isActive && "active text-[var(--color-text-primary)] scale-[1.02] origin-left font-medium",
                isPast && "text-[var(--color-text-dim)]",
                !isActive && !isPast && "text-[var(--color-text-secondary)]"
              )}
              onClick={() => {
                if (parsedLyrics.isSynced && line.timestamp !== null && onSeek) {
                  onSeek(line.timestamp);
                }
              }}
            >
              {parsedLyrics.isSynced && line.timestamp !== null && (
                <span className="lyrics-timestamp inline-block w-12 mr-4 text-xs font-mono text-[var(--color-text-dim)]">
                  {formatTimestamp(line.timestamp)}
                </span>
              )}
              <span>{line.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default LyricsDisplay;
