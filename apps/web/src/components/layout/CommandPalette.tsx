import { useEffect, useRef, useState } from "react";
import { useSearch } from "../../api/queries";
import { useUiStore } from "../../stores/ui";
import { useOpenEntity } from "../../lib/use-open-entity";
import { joinArtists } from "../../lib/format";
import { DegradedBanner } from "../DegradedBanner";
import { SectionDivider } from "../SectionDivider";
import { Spinner } from "../Spinner";
import {
  DiscIcon,
  NoteIcon,
  SearchIcon,
  UserIcon,
} from "../icons";

// The ⌘K command palette (mockup search-trigger target): a modal overlay that
// runs live universal search and routes a pick through the resolve-on-open hook.
// Debounced so keystrokes don't fan out a request each.

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

const THUMB = "size-9 shrink-0 rounded bg-elevated object-cover";
const ROW =
  "flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-hover";

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input.trim(), 200);
  const inputRef = useRef<HTMLInputElement>(null);

  const recent = useUiStore((s) => s.recentSearches);
  const addRecent = useUiStore((s) => s.addRecentSearch);

  const { data, isFetching } = useSearch(query, 6);
  const entity = useOpenEntity();

  useEffect(() => {
    if (!open) return;
    setInput("");
    const handle = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(handle);
  }, [open]);

  if (!open) return null;

  const select = (run: () => void) => {
    if (query.length > 0) addRecent(query);
    run();
    onClose();
  };

  const tracks = data?.results ?? [];
  const artists = data?.artists ?? [];
  const albums = data?.albums ?? [];
  const playlists = data?.playlists ?? [];
  const hasResults =
    tracks.length + artists.length + albums.length + playlists.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-void/70 p-4 pt-[10vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search"
        className="animate-rise flex max-h-[70vh] w-full max-w-xl flex-col overflow-hidden rounded-card border border-line bg-panel shadow-card"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
        }}
      >
        <div className="flex items-center gap-3 border-b border-line-soft px-4">
          <SearchIcon className="size-5 shrink-0 text-muted" />
          <input
            ref={inputRef}
            type="search"
            aria-label="Search songs, albums, artists"
            placeholder="Search songs, albums, artists…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="w-full bg-transparent py-4 text-[15px] text-fg placeholder:text-muted focus:outline-none"
          />
          {isFetching ? <Spinner label="Searching" className="size-4" /> : null}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {query.length === 0 ? (
            <RecentSearches recent={recent} onPick={(q) => setInput(q)} />
          ) : !data ? (
            <p className="px-2 py-6 text-center text-sm text-muted">Searching…</p>
          ) : !hasResults ? (
            <p className="px-2 py-6 text-center text-sm text-muted">
              No results for “{query}”.
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              <DegradedBanner sources={data.degraded_sources} />

              {artists.length > 0 ? (
                <section className="flex flex-col gap-1">
                  <SectionDivider
                    title="Artists"
                    accent="gold"
                    count={artists.length}
                    icon={<UserIcon className="size-4" />}
                  />
                  {artists.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      className={ROW}
                      onClick={() => select(() => entity.openArtist(a))}
                    >
                      {a.image_url ? (
                        <img src={a.image_url} alt="" className={`${THUMB} rounded-full`} />
                      ) : (
                        <span className={`${THUMB} grid place-items-center rounded-full text-muted`}>
                          <UserIcon className="size-4" />
                        </span>
                      )}
                      <span className="truncate text-sm text-fg">{a.name}</span>
                    </button>
                  ))}
                </section>
              ) : null}

              {tracks.length > 0 ? (
                <section className="flex flex-col gap-1">
                  <SectionDivider
                    title="Songs"
                    accent="emerald"
                    count={tracks.length}
                    icon={<NoteIcon className="size-4" />}
                  />
                  {tracks.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      className={ROW}
                      onClick={() => select(() => entity.openTrack(t))}
                    >
                      {t.album?.cover_url ? (
                        <img src={t.album.cover_url} alt="" className={THUMB} />
                      ) : (
                        <span className={`${THUMB} grid place-items-center text-muted`}>
                          <NoteIcon className="size-4" />
                        </span>
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-fg">{t.name}</span>
                        <span className="block truncate text-xs text-muted">
                          {joinArtists(t.artists)}
                        </span>
                      </span>
                    </button>
                  ))}
                </section>
              ) : null}

              {albums.length > 0 ? (
                <section className="flex flex-col gap-1">
                  <SectionDivider
                    title="Albums"
                    accent="teal"
                    count={albums.length}
                    icon={<DiscIcon className="size-4" />}
                  />
                  {albums.map((al) => (
                    <button
                      key={al.id}
                      type="button"
                      className={ROW}
                      onClick={() => select(() => entity.openAlbum(al))}
                    >
                      {al.cover_url ? (
                        <img src={al.cover_url} alt="" className={THUMB} />
                      ) : (
                        <span className={`${THUMB} grid place-items-center text-muted`}>
                          <DiscIcon className="size-4" />
                        </span>
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-fg">{al.name}</span>
                        <span className="block truncate text-xs text-muted">
                          {al.album_artist ?? "Album"}
                        </span>
                      </span>
                    </button>
                  ))}
                </section>
              ) : null}

              {playlists.length > 0 ? (
                <section className="flex flex-col gap-1">
                  <SectionDivider
                    title="Playlists"
                    accent="deezer"
                    count={playlists.length}
                    icon={<NoteIcon className="size-4" />}
                  />
                  {playlists.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className={ROW}
                      onClick={() => select(() => entity.openPlaylist(p))}
                    >
                      {p.cover_url ? (
                        <img src={p.cover_url} alt="" className={THUMB} />
                      ) : (
                        <span className={`${THUMB} grid place-items-center text-muted`}>
                          <NoteIcon className="size-4" />
                        </span>
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-fg">{p.name}</span>
                        <span className="block truncate text-xs text-muted">
                          {p.owner ?? "Playlist"}
                        </span>
                      </span>
                    </button>
                  ))}
                </section>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RecentSearches({
  recent,
  onPick,
}: {
  recent: string[];
  onPick: (query: string) => void;
}) {
  if (recent.length === 0) {
    return (
      <p className="px-2 py-6 text-center text-sm text-muted">
        Search for a song, album, artist, or playlist.
      </p>
    );
  }
  return (
    <section className="flex flex-col gap-1">
      <SectionDivider title="Recent" accent="emerald" />
      {recent.map((q) => (
        <button
          key={q}
          type="button"
          className={ROW}
          onClick={() => onPick(q)}
        >
          <SearchIcon className="size-4 shrink-0 text-muted" />
          <span className="truncate text-sm text-ink-2">{q}</span>
        </button>
      ))}
    </section>
  );
}
