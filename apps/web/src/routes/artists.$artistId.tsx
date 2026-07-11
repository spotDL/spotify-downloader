import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { RefreshCw } from "lucide-react";
import type { AlbumOut, ArtistOut } from "../api/generated/types.gen";
import { useArtist, useForceRefreshArtist } from "../api/queries";
import { useSubmitDownload } from "../api/downloads";
import { isApiError } from "../api/errors";
import { useOpenEntity } from "../lib/use-open-entity";
import { formatFollowers } from "../lib/format";
import { ActionButton } from "../components/ActionButton";
import { AlbumGridCard } from "../components/AlbumGridCard";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { SectionDivider } from "../components/SectionDivider";
import { SourcesPanel } from "../components/SourcesPanel";
import { Spinner } from "../components/Spinner";
import { StatChip } from "../components/StatChip";
import { TrackTable } from "../components/TrackTable";
import { toast } from "../components/Toasts";

export const Route = createFileRoute("/artists/$artistId")({
  component: ArtistPage,
});

function ArtistPage() {
  const { artistId } = Route.useParams();
  const query = useArtist(artistId);

  if (query.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading artist" className="size-8" />
      </div>
    );
  }
  if (query.isError) {
    return (
      <ErrorState
        description={
          isApiError(query.error) ? query.error.message : "Couldn't load this artist."
        }
        action={
          <ActionButton variant="ghost" onClick={() => void query.refetch()}>
            Retry
          </ActionButton>
        }
      />
    );
  }

  return <ArtistDetail artist={query.data} />;
}

function artistInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function ArtistDetail({ artist }: { artist: ArtistOut }) {
  const submit = useSubmitDownload();
  // Force-refresh: re-resolves the artist from its providers (snapshots are
  // permanent, so a plain refetch would re-read the same row forever).
  const { refresh: onRefresh, refreshing } = useForceRefreshArtist(artist.id);
  const tracks = artist.tracks ?? [];
  const genres = artist.genres ?? [];
  const bio = artist.bio?.trim() ? artist.bio.trim() : null;
  // Deezer-sourced artists can carry a raw fan-count in `popularity` (>100); only
  // render it as a 0–100 stat.
  const popularity =
    artist.popularity != null && artist.popularity >= 0 && artist.popularity <= 100
      ? artist.popularity
      : null;

  // The stored discography: metadata-only album previews, each carrying a
  // provider/provider_id source ref for resolve-on-open (like search cards).
  const albums = artist.albums ?? [];

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-center gap-x-5 gap-y-4">
        <div className="shrink-0">
          {artist.image_url ? (
            <img
              src={artist.image_url}
              alt=""
              className="size-28 rounded-full border border-border object-cover"
            />
          ) : (
            <div className="grid size-28 place-items-center rounded-full border border-border bg-elevated font-display text-3xl font-bold text-muted-foreground">
              {artistInitials(artist.name)}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-faint">Artist</p>
          <h1 className="mt-1 font-display text-2xl font-bold tracking-tight text-foreground">
            {artist.name}
          </h1>

          <div className="mt-2.5 flex flex-wrap items-baseline gap-x-5 gap-y-1.5">
            {artist.followers != null ? (
              <StatChip label="followers">{formatFollowers(artist.followers)}</StatChip>
            ) : null}
            {popularity != null ? (
              <StatChip label="popularity">{popularity}</StatChip>
            ) : null}
            {artist.country ? <StatChip label="country">{artist.country}</StatChip> : null}
          </div>

          {genres.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {genres.slice(0, 5).map((g) => (
                <span
                  key={g}
                  className="rounded-md bg-surface px-2 py-0.5 text-xs text-muted-foreground"
                >
                  {g}
                </span>
              ))}
              {genres.length > 5 ? (
                <span className="rounded-md bg-surface px-2 py-0.5 text-xs text-faint">
                  +{genres.length - 5}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* No Enqueue all: an artist is NOT a downloadable batch (Plan 8's
            `unsupported_entity` rule). Enqueue is per-track / per-album. */}
        <ActionButton
          variant="ghost"
          icon={<RefreshCw className="size-4" />}
          disabled={refreshing}
          onClick={() => {
            onRefresh();
            toast.info("Refreshing from providers…");
          }}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </ActionButton>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="flex min-w-0 flex-col gap-8">
          <section className="flex flex-col gap-4">
            <SectionDivider title="Top tracks" count={tracks.length} />
            {tracks.length === 0 ? (
              <EmptyState title="No tracks" description="No top tracks for this artist." />
            ) : (
              <TrackTable tracks={tracks} numbering="index" />
            )}
          </section>

          {albums.length > 0 ? (
            <Discography albums={albums} downloading={submit.isPending} />
          ) : null}
        </div>

        <aside className="flex min-w-0 flex-col gap-5 lg:sticky lg:top-20 lg:h-fit">
          {bio ? (
            <Card title="About">
              <p className="text-sm leading-relaxed text-muted-foreground">{bio}</p>
            </Card>
          ) : null}
          <SourcesPanel entityType="artist" id={artist.id} />
        </aside>
      </div>
    </div>
  );
}

type AlbumFilter = "all" | "album" | "single" | "ep";

const DISCOGRAPHY_TABS: { key: AlbumFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "album", label: "Albums" },
  { key: "single", label: "Singles" },
  { key: "ep", label: "EPs" },
];

/** `"ep"` → `"EP"`, otherwise capitalize the album_type for display. */
function albumTypeLabel(type: string): string {
  const lower = type.toLowerCase();
  if (lower === "ep") return "EP";
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

// The artist discography grid: album-type filter tabs (All / Albums / Singles /
// EPs, each shown only when non-empty) over a grid of `AlbumGridCard`. A stored
// discography album is metadata-only, so opening resolves its `{provider}:album:
// {provider_id}` ref on demand (like a search card) — the same ref downloads it.
function Discography({ albums, downloading }: { albums: AlbumOut[]; downloading: boolean }) {
  const submit = useSubmitDownload();
  const { openAlbum } = useOpenEntity();
  const [filter, setFilter] = useState<AlbumFilter>("all");

  const counts: Record<Exclude<AlbumFilter, "all">, number> = { album: 0, single: 0, ep: 0 };
  for (const a of albums) {
    const type = (a.album_type ?? "").toLowerCase();
    if (type === "album" || type === "single" || type === "ep") counts[type] += 1;
  }
  const tabs = DISCOGRAPHY_TABS.filter((t) => t.key === "all" || counts[t.key] > 0);
  const shown =
    filter === "all"
      ? albums
      : albums.filter((a) => (a.album_type ?? "").toLowerCase() === filter);

  const enqueueAlbum = (album: AlbumOut) => {
    const query =
      album.provider && album.provider_id
        ? `${album.provider}:album:${album.provider_id}`
        : album.id;
    submit.mutate(
      { body: { query } },
      {
        onSuccess: () => toast.info("Added to the download queue."),
        onError: (error) => {
          if (isApiError(error)) toast.fromApiError(error);
          else toast.error("Couldn't start the download.");
        },
      },
    );
  };

  return (
    <section className="flex flex-col gap-4">
      <SectionDivider
        title="Discography"
        count={albums.length}
        action={
          tabs.length > 1 ? (
            <div role="tablist" aria-label="Filter discography" className="flex flex-wrap gap-1.5">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={filter === tab.key}
                  onClick={() => setFilter(tab.key)}
                  className={
                    filter === tab.key
                      ? "rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors"
                      : "rounded-md px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground"
                  }
                >
                  {tab.label}
                </button>
              ))}
            </div>
          ) : undefined
        }
      />
      {shown.length === 0 ? (
        <EmptyState title="No releases" description="Nothing in this category." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {shown.map((al) => (
            <AlbumGridCard
              key={al.id}
              name={al.name}
              coverUrl={al.cover_url}
              year={al.year}
              subtitle={al.album_type ? albumTypeLabel(al.album_type) : (al.album_artist ?? "Album")}
              onOpen={() => openAlbum({ provider: al.provider, provider_id: al.provider_id })}
              onDownload={() => enqueueAlbum(al)}
              downloading={downloading || submit.isPending}
            />
          ))}
        </div>
      )}
    </section>
  );
}
