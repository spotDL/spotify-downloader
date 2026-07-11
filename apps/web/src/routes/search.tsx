import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import { ChevronRight, Disc3, Music, User } from "lucide-react";
import type {
  AlbumOut,
  ArtistOut,
  PlaylistOut,
  TrackOut,
} from "../api/generated/types.gen";
import { useSearch as useSearchQuery } from "../api/queries";
import { useSubmitDownload } from "../api/downloads";
import { isApiError } from "../api/errors";
import { useOpenEntity } from "../lib/use-open-entity";
import {
  formatDuration,
  formatFollowers,
  joinArtists,
  joinMeta,
} from "../lib/format";
import { cn } from "../lib/utils";
import { useUiStore } from "../stores/ui";
import { AlbumGridCard } from "../components/AlbumGridCard";
import { DegradedBanner } from "../components/DegradedBanner";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { toast } from "../components/Toasts";
import { Meter, scoreColor } from "../components/ui/meter";

export const Route = createFileRoute("/search")({
  validateSearch: (search: Record<string, unknown>): { q?: string } => {
    const q = search.q;
    return typeof q === "string" && q.length > 0 ? { q } : {};
  },
  component: SearchResults,
});

type Filter = "all" | "songs" | "artists" | "albums" | "playlists";

// A subtle one-shot stagger across the result sections (respecting
// reduce-motion; the route root already runs the page-enter fade).
const sectionList = {
  hidden: {},
  show: { transition: { staggerChildren: 0.03 } },
};
const sectionItem = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] as const },
  },
};

// Eyebrow section header — the Control Room label + mono count.
function SectionHeader({
  title,
  count,
  icon,
}: {
  title: string;
  count: number;
  icon?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 px-1">
      {icon ? <span className="text-faint">{icon}</span> : null}
      <h2 className="text-xs font-medium uppercase tracking-wider text-faint">
        {title}
      </h2>
      <span className="font-mono text-xs text-faint tnum">{count}</span>
    </div>
  );
}

// A cover/avatar thumbnail for a dense result row.
function RowThumb({
  src,
  circle,
}: {
  src?: string | null;
  circle?: boolean;
}) {
  const shape = circle ? "rounded-full" : "rounded-md";
  if (src != null && src !== "") {
    return (
      <img
        src={src}
        alt=""
        loading="lazy"
        className={cn(
          "size-11 shrink-0 border border-border object-cover",
          shape,
        )}
      />
    );
  }
  return (
    <span
      aria-hidden
      className={cn(
        "grid size-11 shrink-0 place-items-center border border-border bg-surface text-faint",
        shape,
      )}
    >
      {circle ? (
        <User className="size-5" />
      ) : (
        <span className="text-base leading-none">♪</span>
      )}
    </span>
  );
}

// Right-aligned mono facts + a Meter for a 0–100 match/relevance score.
function RowFacts({
  text,
  score,
}: {
  text?: string;
  score?: number | null;
}) {
  if ((text === undefined || text === "") && score == null) return null;
  return (
    <div className="flex shrink-0 flex-col items-end gap-1">
      {text !== undefined && text !== "" ? (
        <span className="font-mono text-xs text-muted-foreground tnum">
          {text}
        </span>
      ) : null}
      {score != null ? (
        <Meter
          value={score}
          max={100}
          cells={10}
          size="sm"
          color={scoreColor(score)}
          label={`Popularity ${score}`}
          className="w-14"
        />
      ) : null}
    </div>
  );
}

// A dense console row that links to an entity but opens it via resolve-on-click
// (CONTRACT — spec §6; the raw href is the accessible/fallback target).
function LinkRow({
  href,
  onSelect,
  eyebrow,
  title,
  subtitle,
  thumb,
  facts,
}: {
  href: string;
  onSelect: () => void;
  eyebrow: string;
  title: string;
  subtitle?: string;
  thumb: ReactNode;
  facts?: ReactNode;
}) {
  return (
    <a
      href={href}
      onClick={(e) => {
        e.preventDefault();
        onSelect();
      }}
      className="group flex items-center gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-elevated"
    >
      {thumb}
      <div className="min-w-0 flex-1">
        <span className="block text-xs font-medium uppercase tracking-wider text-faint">
          {eyebrow}
        </span>
        <span className="block truncate text-sm font-medium text-foreground transition-colors group-hover:text-primary">
          {title}
        </span>
        {subtitle !== undefined && subtitle !== "" ? (
          <span className="block truncate text-xs text-muted-foreground">
            {subtitle}
          </span>
        ) : null}
      </div>
      {facts}
      <ChevronRight className="size-4 shrink-0 text-faint" />
    </a>
  );
}

function SearchResults() {
  const { q } = Route.useSearch();
  const query = q ?? "";
  const { data, isPending, isError, isFetching } = useSearchQuery(query);
  const [filter, setFilter] = useState<Filter>("all");
  const reduceMotion = useReducedMotion();
  const addRecent = useUiStore((s) => s.addRecentSearch);

  useEffect(() => {
    if (query.trim().length > 0) addRecent(query);
  }, [query, addRecent]);

  if (query.trim().length === 0) {
    return <EmptySearch />;
  }

  // `useSearch` is disabled for an empty query, so a non-empty query that hasn't
  // resolved yet is genuinely loading.
  if (isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Searching" className="size-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Search failed"
        description="Something went wrong searching. Try again in a moment."
      />
    );
  }

  const tracks = data.results;
  const artists = data.artists ?? [];
  const albums = data.albums ?? [];
  const playlists = data.playlists ?? [];
  const total = tracks.length + artists.length + albums.length + playlists.length;

  const counts: Record<Filter, number> = {
    all: total,
    songs: tracks.length,
    artists: artists.length,
    albums: albums.length,
    playlists: playlists.length,
  };
  const show = (f: Filter) => filter === "all" || filter === f;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="font-display text-2xl font-bold tracking-tight">
          Results for “{query}”
        </h1>
        {isFetching ? <Spinner label="Refreshing results" /> : null}
      </div>

      <DegradedBanner sources={data.degraded_sources} />

      {total === 0 ? (
        <EmptyState
          title="No results"
          description="Nothing matched that search. Try different words, or paste a link on the home page."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[180px_1fr]">
          <FilterRail filter={filter} counts={counts} onChange={setFilter} />
          <motion.div
            className="flex min-w-0 flex-col gap-8"
            variants={reduceMotion ? undefined : sectionList}
            initial={reduceMotion ? false : "hidden"}
            animate="show"
          >
            {show("artists") && artists.length > 0 ? (
              <ArtistsSection artists={artists} />
            ) : null}
            {show("songs") && tracks.length > 0 ? (
              <SongsSection tracks={tracks} />
            ) : null}
            {show("albums") && albums.length > 0 ? (
              <AlbumsSection albums={albums} />
            ) : null}
            {show("playlists") && playlists.length > 0 ? (
              <PlaylistsSection playlists={playlists} />
            ) : null}
          </motion.div>
        </div>
      )}
    </div>
  );
}

function EmptySearch() {
  const navigate = useNavigate();
  const recent = useUiStore((s) => s.recentSearches);
  const clear = useUiStore((s) => s.clearRecentSearches);
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-8">
      <EmptyState
        title="Search spotDL"
        description="Press ⌘K, or type a track, album, artist, or playlist to see results."
      />
      {recent.length > 0 ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-faint">
              Recent searches
            </span>
            <button
              type="button"
              onClick={clear}
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
    </div>
  );
}

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "songs", label: "Songs" },
  { key: "artists", label: "Artists" },
  { key: "albums", label: "Albums" },
  { key: "playlists", label: "Playlists" },
];

function FilterRail({
  filter,
  counts,
  onChange,
}: {
  filter: Filter;
  counts: Record<Filter, number>;
  onChange: (f: Filter) => void;
}) {
  return (
    <aside className="flex flex-col gap-3">
      <div
        className="flex flex-row flex-wrap gap-1 lg:flex-col"
        role="tablist"
        aria-label="Filter results"
        aria-orientation="vertical"
      >
        {FILTERS.filter((f) => f.key === "all" || counts[f.key] > 0).map((f) => {
          const active = filter === f.key;
          return (
            <button
              key={f.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onChange(f.key)}
              className={cn(
                "flex items-center justify-between gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-elevated hover:text-foreground",
              )}
            >
              <span>{f.label}</span>
              <span
                className={cn(
                  "font-mono text-xs tnum",
                  active ? "text-primary-foreground/70" : "text-faint",
                )}
              >
                {counts[f.key]}
              </span>
            </button>
          );
        })}
      </div>
      <p className="hidden px-1 text-xs text-faint lg:block">
        <span className="font-mono text-muted-foreground tnum">{counts.all}</span>{" "}
        {counts.all === 1 ? "result" : "results"}
      </p>
    </aside>
  );
}

function ArtistsSection({ artists }: { artists: ArtistOut[] }) {
  const { openArtist } = useOpenEntity();
  return (
    <motion.section variants={sectionItem} className="flex flex-col gap-3">
      <SectionHeader
        title="Artists"
        count={artists.length}
        icon={<User className="size-4" />}
      />
      <div className="rounded-lg border border-border bg-card p-1">
        {artists.map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => openArtist(a)}
            className="group flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-elevated"
          >
            <RowThumb src={a.image_url} circle />
            <div className="min-w-0 flex-1">
              <span className="block text-xs font-medium uppercase tracking-wider text-faint">
                Artist
              </span>
              <span className="block truncate text-sm font-medium text-foreground transition-colors group-hover:text-primary">
                {a.name}
              </span>
            </div>
            <RowFacts
              text={a.followers != null ? formatFollowers(a.followers) : undefined}
              score={a.popularity}
            />
            <ChevronRight className="size-4 shrink-0 text-faint" />
          </button>
        ))}
      </div>
    </motion.section>
  );
}

function SongsSection({ tracks }: { tracks: TrackOut[] }) {
  const { openTrack } = useOpenEntity();
  return (
    <motion.section variants={sectionItem} className="flex flex-col gap-3">
      <SectionHeader
        title="Songs"
        count={tracks.length}
        icon={<Music className="size-4" />}
      />
      <div className="rounded-lg border border-border bg-card p-1">
        {tracks.map((track) => (
          <LinkRow
            key={track.id}
            href={`/tracks/${track.id}`}
            onSelect={() => openTrack(track)}
            eyebrow="Song"
            title={track.name}
            subtitle={joinArtists(track.artists)}
            thumb={<RowThumb src={track.cover_url ?? track.album?.cover_url} />}
            facts={
              <RowFacts
                text={formatDuration(track.duration_ms)}
                score={track.popularity}
              />
            }
          />
        ))}
      </div>
    </motion.section>
  );
}

function AlbumsSection({ albums }: { albums: AlbumOut[] }) {
  const { openAlbum } = useOpenEntity();
  const [view, setView] = useState<"grid" | "list">("grid");
  const submit = useSubmitDownload();

  const enqueue = (id: string) =>
    submit.mutate(
      { body: { query: id } },
      {
        onSuccess: () => toast.info("Added to the download queue."),
        onError: (error) => {
          if (isApiError(error)) toast.fromApiError(error);
          else toast.error("Couldn't start the download.");
        },
      },
    );

  return (
    <motion.section variants={sectionItem} className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <SectionHeader
          title="Albums"
          count={albums.length}
          icon={<Disc3 className="size-4" />}
        />
        <div className="flex gap-0.5 rounded-md border border-border bg-surface p-0.5">
          {(["grid", "list"] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => setView(v)}
              className={cn(
                "rounded px-2.5 py-1 text-xs font-medium capitalize transition-colors",
                view === v
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {view === "list" ? (
        <div className="rounded-lg border border-border bg-card p-1">
          {albums.map((al) => (
            <LinkRow
              key={al.id}
              href={`/albums/${al.id}`}
              onSelect={() => openAlbum(al)}
              eyebrow="Album"
              title={al.name}
              subtitle={al.album_artist ?? undefined}
              thumb={<RowThumb src={al.cover_url} />}
              facts={
                <RowFacts
                  text={joinMeta([
                    al.year,
                    al.track_count != null ? `${al.track_count} tracks` : undefined,
                  ])}
                  score={al.popularity}
                />
              }
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {albums.map((al) => (
            <AlbumGridCard
              key={al.id}
              name={al.name}
              coverUrl={al.cover_url}
              year={al.year}
              subtitle={al.album_artist ?? "Album"}
              onOpen={() => openAlbum(al)}
              onDownload={() => enqueue(al.id)}
              downloading={submit.isPending}
            />
          ))}
        </div>
      )}
    </motion.section>
  );
}

function PlaylistsSection({ playlists }: { playlists: PlaylistOut[] }) {
  const { openPlaylist } = useOpenEntity();
  return (
    <motion.section variants={sectionItem} className="flex flex-col gap-3">
      <SectionHeader
        title="Playlists"
        count={playlists.length}
        icon={<Music className="size-4" />}
      />
      <div className="rounded-lg border border-border bg-card p-1">
        {playlists.map((p) => (
          <LinkRow
            key={p.id}
            href={`/playlists/${p.id}`}
            onSelect={() => openPlaylist(p)}
            eyebrow="Playlist"
            title={p.name}
            subtitle={p.owner ?? undefined}
            thumb={<RowThumb src={p.cover_url} />}
          />
        ))}
      </div>
    </motion.section>
  );
}
