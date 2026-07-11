import { useEffect, useState } from "react";
import { Disc3, ListMusic, Loader2, Music, Search, User } from "lucide-react";
import { useSearch } from "../../api/queries";
import { useUiStore } from "../../stores/ui";
import { useOpenEntity } from "../../lib/use-open-entity";
import { joinArtists } from "../../lib/format";
import { cn } from "../../lib/utils";
import { DegradedBanner } from "../DegradedBanner";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../ui/command";

// The ⌘K command palette: a cmdk dialog that runs live universal search and
// routes a pick through the resolve-on-open hook. Debounced so keystrokes don't
// fan out a request each. Server-side search, so cmdk's own filtering is off.

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

const THUMB =
  "flex size-9 shrink-0 items-center justify-center overflow-hidden rounded border border-border bg-elevated text-faint";

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input.trim(), 200);

  const recent = useUiStore((s) => s.recentSearches);
  const addRecent = useUiStore((s) => s.addRecentSearch);

  const { data, isFetching } = useSearch(query, 6);
  const entity = useOpenEntity();

  useEffect(() => {
    if (open) setInput("");
  }, [open]);

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
    <CommandDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title="Search"
      description="Search songs, albums, artists, and playlists"
      shouldFilter={false}
    >
      <CommandInput
        value={input}
        onValueChange={setInput}
        placeholder="Search songs, albums, artists…"
      />
      <CommandList>
        {query.length === 0 ? (
          recent.length === 0 ? (
            <CommandEmpty>Search for a song, album, artist, or playlist.</CommandEmpty>
          ) : (
            <CommandGroup heading="Recent">
              {recent.map((q) => (
                <CommandItem key={q} value={`recent:${q}`} onSelect={() => setInput(q)}>
                  <Search className="size-4" />
                  <span className="truncate">{q}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          )
        ) : isFetching && !data ? (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Searching…
          </div>
        ) : !hasResults ? (
          <CommandEmpty>No results for “{query}”.</CommandEmpty>
        ) : (
          <>
            {data && data.degraded_sources.length > 0 ? (
              <div className="p-1">
                <DegradedBanner sources={data.degraded_sources} />
              </div>
            ) : null}

            {artists.length > 0 ? (
              <CommandGroup heading="Artists">
                {artists.map((a) => (
                  <CommandItem
                    key={a.id}
                    value={`artist:${a.id}`}
                    onSelect={() => select(() => entity.openArtist(a))}
                    className="gap-3"
                  >
                    {a.image_url ? (
                      <img src={a.image_url} alt="" className={cn(THUMB, "rounded-full")} />
                    ) : (
                      <span className={cn(THUMB, "rounded-full")}>
                        <User className="size-4" />
                      </span>
                    )}
                    <span className="truncate">{a.name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}

            {tracks.length > 0 ? (
              <CommandGroup heading="Songs">
                {tracks.map((t) => (
                  <CommandItem
                    key={t.id}
                    value={`track:${t.id}`}
                    onSelect={() => select(() => entity.openTrack(t))}
                    className="gap-3"
                  >
                    {t.album?.cover_url ? (
                      <img src={t.album.cover_url} alt="" className={THUMB} />
                    ) : (
                      <span className={THUMB}>
                        <Music className="size-4" />
                      </span>
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{t.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {joinArtists(t.artists)}
                      </span>
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}

            {albums.length > 0 ? (
              <CommandGroup heading="Albums">
                {albums.map((al) => (
                  <CommandItem
                    key={al.id}
                    value={`album:${al.id}`}
                    onSelect={() => select(() => entity.openAlbum(al))}
                    className="gap-3"
                  >
                    {al.cover_url ? (
                      <img src={al.cover_url} alt="" className={THUMB} />
                    ) : (
                      <span className={THUMB}>
                        <Disc3 className="size-4" />
                      </span>
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{al.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {al.album_artist ?? "Album"}
                      </span>
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}

            {playlists.length > 0 ? (
              <CommandGroup heading="Playlists">
                {playlists.map((p) => (
                  <CommandItem
                    key={p.id}
                    value={`playlist:${p.id}`}
                    onSelect={() => select(() => entity.openPlaylist(p))}
                    className="gap-3"
                  >
                    {p.cover_url ? (
                      <img src={p.cover_url} alt="" className={THUMB} />
                    ) : (
                      <span className={THUMB}>
                        <ListMusic className="size-4" />
                      </span>
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{p.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {p.owner ?? "Playlist"}
                      </span>
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
