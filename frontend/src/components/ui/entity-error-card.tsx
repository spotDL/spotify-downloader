import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";

// ────────────────────────────────────────────────────────────────────────────
// Error classification
// ────────────────────────────────────────────────────────────────────────────

export type EntityErrorKind = "not_found" | "load_failed";

export interface ClassifiedEntityError {
  kind: EntityErrorKind;
  heading: string;
  description: string;
  rawMessage: string;
}

const NOT_FOUND_PATTERNS = [
  "not a valid uuid",
  "could not resolve",
  "invalid entity id",
];

function isNotFoundError(message: string): boolean {
  const lower = message.toLowerCase();
  return NOT_FOUND_PATTERNS.some((p) => lower.includes(p));
}

export function classifyEntityError(
  error: unknown,
  entityLabel: string,
): ClassifiedEntityError {
  const rawMessage =
    error instanceof Error
      ? error.message
      : String(error ?? "An error occurred");

  if (isNotFoundError(rawMessage)) {
    return {
      kind: "not_found",
      heading: `${entityLabel} Not Found`,
      description:
        "The ID in the URL doesn't match any known entity in the database. Try searching for the entity by name or paste a Spotify / YouTube URL in the search bar.",
      rawMessage,
    };
  }

  // HTTP 404 pattern from API client
  if (
    rawMessage.includes("404") ||
    rawMessage.toLowerCase().includes("not found")
  ) {
    return {
      kind: "not_found",
      heading: `${entityLabel} Not Found`,
      description: `This ${entityLabel.toLowerCase()} doesn't exist or may have been removed. You can search for it by name or URL.`,
      rawMessage,
    };
  }

  return {
    kind: "load_failed",
    heading: `Failed to Load ${entityLabel}`,
    description:
      "Something went wrong while fetching the data. Please try again — if the problem persists, the service may be temporarily unavailable.",
    rawMessage,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// EntityErrorCard component
// ────────────────────────────────────────────────────────────────────────────

const ENTITY_LABELS: Record<EntityType, string> = {
  album: "Album",
  artist: "Artist",
  song: "Track",
  playlist: "Playlist",
};

type EntityType = "album" | "artist" | "song" | "playlist";

interface EntityErrorCardProps {
  entityType: EntityType;
  /** Pass `null` for "entity not found" (query returned nothing, no error object). */
  error: unknown;
  entityId: string;
}

export function EntityErrorCard({
  entityType,
  error,
  entityId,
}: EntityErrorCardProps) {
  const [showDetails, setShowDetails] = useState(false);
  const entityLabel = ENTITY_LABELS[entityType];

  const classified =
    error != null
      ? classifyEntityError(error, entityLabel)
      : {
          kind: "not_found" as EntityErrorKind,
          heading: `${entityLabel} Not Found`,
          description: `This ${entityLabel.toLowerCase()} doesn't exist or may have been removed. Try searching for it by name or paste a URL in the search bar.`,
          rawMessage: "",
        };

  const isNotFound = classified.kind === "not_found";

  return (
    <Card
      variant="bordered"
      className={`max-w-xl mx-auto ${isNotFound ? "border-zinc-800" : "border-red-900/50"}`}
    >
      <CardContent className="py-10 flex flex-col items-center text-center gap-5">
        {/* Icon */}
        <div
          className={`w-14 h-14 rounded-full flex items-center justify-center ${
            isNotFound ? "bg-zinc-800/60" : "bg-red-950/40"
          }`}
        >
          {isNotFound ? (
            <svg
              className="w-7 h-7 text-zinc-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          ) : (
            <svg
              className="w-7 h-7 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v3m0 3.5h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
          )}
        </div>

        {/* Heading & description */}
        <div className="space-y-2">
          <h2
            className={`text-lg font-semibold ${
              isNotFound ? "text-zinc-200" : "text-red-400"
            }`}
          >
            {classified.heading}
          </h2>
          <p className="text-sm text-zinc-400 max-w-sm leading-relaxed">
            {classified.description}
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
          <Link
            to="/search"
            search={{ q: entityId } as Record<string, string>}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-needle/10 hover:bg-accent-needle/20 border border-accent-needle/30 text-accent-needle text-sm font-medium transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            Search instead
          </Link>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700/50 text-zinc-300 text-sm font-medium transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            </svg>
            Back to home
          </Link>
        </div>

        {/* Collapsible details */}
        <div className="w-full pt-1">
          <button
            onClick={() => setShowDetails((v) => !v)}
            className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors inline-flex items-center gap-1"
          >
            <svg
              className={`w-3 h-3 transition-transform ${showDetails ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
            {showDetails ? "Hide details" : "Show details"}
          </button>
          {showDetails && (
            <div className="mt-3 p-3 rounded-lg bg-zinc-900/60 border border-zinc-800/50 text-left space-y-1.5">
              <p className="text-xs text-zinc-500">
                <span className="text-zinc-600">ID: </span>
                <code className="font-mono text-zinc-400 break-all">
                  {entityId}
                </code>
              </p>
              {classified.rawMessage && (
                <p className="text-xs text-zinc-500">
                  <span className="text-zinc-600">Error: </span>
                  <code className="font-mono text-zinc-400 break-all">
                    {classified.rawMessage}
                  </code>
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
