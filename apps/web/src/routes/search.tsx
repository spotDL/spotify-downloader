import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
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
import { joinArtists } from "../lib/format";
import { useUiStore } from "../stores/ui";
import { AlbumGridCard } from "../components/AlbumGridCard";
import { DegradedBanner } from "../components/DegradedBanner";
import { EmptyState } from "../components/EmptyState";
import { EntityCard } from "../components/EntityCard";
import { ErrorState } from "../components/ErrorState";
import { SectionDivider } from "../components/SectionDivider";
import { Spinner } from "../components/Spinner";
import { toast } from "../components/Toasts";
import { DiscIcon, NoteIcon, UserIcon } from "../components/icons";

export const Route = createFileRoute("/search")({
  validateSearch: (search: Record<string, unknown>): { q?: string } => {
    const q = search.q;
    return typeof q === "string" && q.length > 0 ? { q } : {};
  },
  component: SearchResults,
});

type Filter = "all" | "songs" | "artists" | "albums" | "playlists";

function SearchResults() {
  const { q } = Route.useSearch();
  const query = q ?? "";
  const { data, isPending, isError, isFetching } = useSearchQuery(query);
  const [filter, setFilter] = useState<Filter>("all");
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
      <div className="mx-auto max-w-[1080px] px-6 py-16">
        <ErrorState
          title="Search failed"
          description="Something went wrong searching. Try again in a moment."
        />
      </div>
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
    <div className="mx-auto flex max-w-[1080px] flex-col gap-5 px-6 py-7">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-fg">
          Results for “{query}”
        </h1>
        {isFetching ? <Spinner label="Refreshing results" /> : null}
      </div>

      <DegradedBanner sources={data.degraded_sources} />

      <FilterTabs filter={filter} counts={counts} onChange={setFilter} />

      {total === 0 ? (
        <EmptyState
          title="No results"
          description="Nothing matched that search. Try different words, or paste a link on the home page."
        />
      ) : (
        <div className="flex flex-col gap-8">
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
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-12">
      <EmptyState
        title="Search spotDL"
        description="Press ⌘K, or type a track, album, artist, or playlist to see results."
      />
      {recent.length > 0 ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <SectionDivider title="Recent searches" accent="emerald" />
            <button
              type="button"
              onClick={clear}
              className="font-mono text-[11px] text-muted hover:text-fg"
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
                className="rounded-full border border-line-soft bg-elevated px-3 py-1.5 text-sm text-ink-2 transition-colors hover:bg-hover hover:text-fg"
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

function FilterTabs({
  filter,
  counts,
  onChange,
}: {
  filter: Filter;
  counts: Record<Filter, number>;
  onChange: (f: Filter) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter results">
      {FILTERS.filter((f) => f.key === "all" || counts[f.key] > 0).map((f) => (
        <button
          key={f.key}
          type="button"
          role="tab"
          aria-selected={filter === f.key}
          onClick={() => onChange(f.key)}
          className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
            filter === f.key
              ? "border-fg bg-fg text-void"
              : "border-line text-ink-2 hover:bg-surface hover:text-fg"
          }`}
        >
          {f.label}
          <span className="ml-1.5 font-mono tabular-nums opacity-60">
            {counts[f.key]}
          </span>
        </button>
      ))}
    </div>
  );
}

function ArtistsSection({ artists }: { artists: ArtistOut[] }) {
  const { openArtist } = useOpenEntity();
  return (
    <section className="flex flex-col gap-4">
      <SectionDivider
        title="Artists"
        accent="gold"
        count={artists.length}
        icon={<UserIcon className="size-4" />}
      />
      <div className="flex flex-wrap gap-5">
        {artists.map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => openArtist(a)}
            className="group flex w-24 flex-col items-center gap-2 text-center"
          >
            {a.image_url ? (
              <img
                src={a.image_url}
                alt=""
                className="size-24 rounded-full object-cover shadow-card transition-transform group-hover:-translate-y-1"
              />
            ) : (
              <span className="grid size-24 place-items-center rounded-full bg-elevated text-muted transition-transform group-hover:-translate-y-1">
                <UserIcon className="size-8" />
              </span>
            )}
            <span className="w-full truncate text-sm font-medium text-fg">{a.name}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function SongsSection({ tracks }: { tracks: TrackOut[] }) {
  const { openTrack } = useOpenEntity();
  return (
    <section className="flex flex-col gap-4">
      <SectionDivider
        title="Songs"
        accent="emerald"
        count={tracks.length}
        icon={<NoteIcon className="size-4" />}
      />
      <ul className="grid gap-3 sm:grid-cols-2">
        {tracks.map((track) => (
          <li key={track.id}>
            <EntityCard
              type="track"
              id={track.id}
              name={track.name}
              subtitle={joinArtists(track.artists)}
              imageUrl={track.cover_url ?? track.album?.cover_url}
              onSelect={() => openTrack(track)}
            />
          </li>
        ))}
      </ul>
    </section>
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
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <SectionDivider
          title="Albums"
          accent="teal"
          count={albums.length}
          icon={<DiscIcon className="size-4" />}
        />
        <div className="flex gap-1 rounded-lg border border-line bg-surface p-0.5">
          {(["grid", "list"] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => setView(v)}
              className={`rounded-md px-2.5 py-1 text-xs font-semibold capitalize transition-colors ${
                view === v ? "bg-emerald text-void" : "text-muted hover:text-fg"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {view === "list" ? (
        <ul className="grid gap-3 sm:grid-cols-2">
          {albums.map((al) => (
            <li key={al.id}>
              <EntityCard
                type="album"
                id={al.id}
                name={al.name}
                subtitle={al.album_artist ?? undefined}
                imageUrl={al.cover_url}
                onSelect={() => openAlbum(al)}
              />
            </li>
          ))}
        </ul>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
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
    </section>
  );
}

function PlaylistsSection({ playlists }: { playlists: PlaylistOut[] }) {
  const { openPlaylist } = useOpenEntity();
  return (
    <section className="flex flex-col gap-4">
      <SectionDivider
        title="Playlists"
        accent="deezer"
        count={playlists.length}
        icon={<NoteIcon className="size-4" />}
      />
      <ul className="grid gap-3 sm:grid-cols-2">
        {playlists.map((p) => (
          <li key={p.id}>
            <EntityCard
              type="playlist"
              id={p.id}
              name={p.name}
              subtitle={p.owner ?? undefined}
              imageUrl={p.cover_url}
              onSelect={() => openPlaylist(p)}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
