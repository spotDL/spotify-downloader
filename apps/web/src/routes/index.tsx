import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import { Search } from "lucide-react";
import { useResolve } from "../api/queries";
import type { EntityEnvelope } from "../api/generated/types.gen";
import { reportError } from "../lib/report-error";
import { toast } from "../components/Toasts";
import { Button } from "../components/Button";
import { DegradedBanner } from "../components/DegradedBanner";
import { Input } from "../components/Input";
import { Spinner } from "../components/Spinner";
import { useUiStore } from "../stores/ui";

export const Route = createFileRoute("/")({
  component: Home,
});

// Navigation target for a resolved entity.
type ResolveTarget =
  | { kind: "track"; trackId: string; title: string }
  | { kind: "album" | "artist" | "playlist"; id: string; title: string };

function entityTarget(entity: EntityEnvelope): ResolveTarget | null {
  if (entity.type === "track" && entity.track) {
    return { kind: "track", trackId: entity.track.id, title: entity.track.name };
  }
  if (entity.type === "album" && entity.album) {
    return { kind: "album", id: entity.album.id, title: entity.album.name };
  }
  if (entity.type === "artist" && entity.artist) {
    return { kind: "artist", id: entity.artist.id, title: entity.artist.name };
  }
  if (entity.type === "playlist" && entity.playlist) {
    return { kind: "playlist", id: entity.playlist.id, title: entity.playlist.name };
  }
  return null;
}

const HINTS = ["Spotify URL", "YouTube URL", "Artist - Song"];

// A subtle one-shot stagger on the hero (respecting reduce-motion).
const heroContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.03 } },
};
const heroLine = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.32, ease: [0.16, 1, 0.3, 1] as const },
  },
};

function Home() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [degraded, setDegraded] = useState<{
    sources: string[];
    trackId: string;
    title: string;
  } | null>(null);

  const resolve = useResolve();
  const recent = useUiStore((s) => s.recentSearches);
  const clearRecent = useUiStore((s) => s.clearRecentSearches);

  const goToTrack = (trackId: string) =>
    navigate({ to: "/tracks/$trackId", params: { trackId } });

  const goToTarget = (target: ResolveTarget) => {
    if (target.kind === "track") return goToTrack(target.trackId);
    if (target.kind === "album")
      return navigate({ to: "/albums/$albumId", params: { albumId: target.id } });
    if (target.kind === "artist")
      return navigate({ to: "/artists/$artistId", params: { artistId: target.id } });
    return navigate({ to: "/playlists/$playlistId", params: { playlistId: target.id } });
  };

  const onResolve = (e: React.FormEvent) => {
    e.preventDefault();
    const value = url.trim();
    if (value.length === 0) return;
    setDegraded(null);
    resolve.mutate(
      { body: { query: value } },
      {
        onSuccess: (res) => {
          const target = entityTarget(res.entity);
          if (!target) {
            toast.info("That link resolved to something spotDL can't display yet.");
            return;
          }
          // Surface any degraded sources before leaving the page; a clean
          // resolve navigates straight through (CONTRACT — spec §6). The
          // banner's continue button only supports tracks; other kinds
          // navigate directly (their pages render their own degraded state).
          if (res.degraded_sources.length > 0 && target.kind === "track") {
            setDegraded({
              sources: res.degraded_sources,
              trackId: target.trackId,
              title: target.title,
            });
            return;
          }
          void goToTarget(target);
        },
        onError: (err) => reportError(err, "Couldn't open that link."),
      },
    );
  };

  return (
    <div className="mx-auto flex min-h-[64vh] max-w-2xl flex-col justify-center gap-10 py-8 sm:py-16">
      <motion.section
        variants={reduceMotion ? undefined : heroContainer}
        initial={reduceMotion ? false : "hidden"}
        animate="show"
        className="flex flex-col gap-6"
      >
        <motion.p
          variants={reduceMotion ? undefined : heroLine}
          className="text-xs font-medium uppercase tracking-wider text-faint"
        >
          Music catalog console
        </motion.p>

        <motion.h1
          variants={reduceMotion ? undefined : heroLine}
          className="font-display text-4xl font-bold tracking-tight sm:text-5xl"
        >
          Download music from anywhere
        </motion.h1>

        <motion.p
          variants={reduceMotion ? undefined : heroLine}
          className="max-w-lg text-muted-foreground"
        >
          Search for a track, album, artist, or playlist — or paste a link.
        </motion.p>

        <motion.form
          variants={reduceMotion ? undefined : heroLine}
          role="search"
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            const next = query.trim();
            if (next.length > 0) void navigate({ to: "/search", search: { q: next } });
          }}
        >
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-faint" />
            <Input
              type="search"
              aria-label="Search"
              placeholder="e.g. Daft Punk — Get Lucky"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-12 pl-11 text-base"
            />
          </div>
          <Button type="submit" className="h-12 px-6 text-base font-semibold">
            Search
          </Button>
        </motion.form>

        <motion.div
          variants={reduceMotion ? undefined : heroLine}
          className="flex flex-wrap items-center gap-2"
        >
          <span className="text-xs font-medium uppercase tracking-wider text-faint">
            Accepts
          </span>
          {HINTS.map((hint) => (
            <span
              key={hint}
              className="rounded-full border border-border bg-card px-2.5 py-1 font-mono text-xs text-muted-foreground tnum"
            >
              {hint}
            </span>
          ))}
        </motion.div>
      </motion.section>

      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={onResolve}>
        <Input
          type="text"
          aria-label="Paste a link"
          placeholder="Paste a Spotify or other supported link…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" variant="secondary" disabled={resolve.isPending}>
          {resolve.isPending ? <Spinner label="Opening" /> : "Open"}
        </Button>
      </form>

      {recent.length > 0 ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-faint">
              Recent searches
            </span>
            <button
              type="button"
              onClick={clearRecent}
              className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              clear
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {recent.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => void navigate({ to: "/search", search: { q: r } })}
                className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground"
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {degraded ? (
        <div className="flex flex-col gap-3">
          <DegradedBanner sources={degraded.sources} />
          <div className="flex justify-end">
            <Button onClick={() => void goToTrack(degraded.trackId)}>
              Continue to “{degraded.title}”
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
