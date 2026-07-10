import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import type { AlbumOut, ArtistOut } from "../api/generated/types.gen";
import { useArtist, useForceRefreshArtist } from "../api/queries";
import { useSubmitDownload } from "../api/downloads";
import { isApiError } from "../api/errors";
import { useOpenEntity } from "../lib/use-open-entity";
import { formatFollowers } from "../lib/format";
import { ActionButton } from "../components/ActionButton";
import { AlbumGridCard } from "../components/AlbumGridCard";
import { Badge } from "../components/Badge";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { HeroBackdrop } from "../components/HeroBackdrop";
import { SectionDivider } from "../components/SectionDivider";
import { SourcesPanel, StatsCard } from "../components/SourcesPanel";
import { Spinner } from "../components/Spinner";
import { StatChip } from "../components/StatChip";
import { TrackTable } from "../components/TrackTable";
import { DiscIcon, NoteIcon, RefreshIcon } from "../components/icons";
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
      <div className="mx-auto max-w-[1080px] px-6 py-16">
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
      </div>
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
  const hasStats = artist.followers != null || popularity != null;

  // The stored discography: metadata-only album previews, each carrying a
  // provider/provider_id source ref for resolve-on-open (like search cards).
  const albums = artist.albums ?? [];

  return (
    <div>
      <div className="grain relative overflow-hidden border-b border-line-soft">
        <HeroBackdrop coverUrl={artist.header_url ?? artist.image_url} />
        <div className="relative z-[2] mx-auto max-w-[1080px] px-6">
          <div className="flex flex-col items-start gap-7 pt-11 pb-8 sm:flex-row sm:items-end">
            <div className="relative shrink-0">
              <div
                aria-hidden
                className="absolute -inset-2.5 rounded-full opacity-50 blur-2xl"
                style={{
                  background: "conic-gradient(from 0deg, #00d084, #4ecdc4, #00d084)",
                }}
              />
              {artist.image_url ? (
                <img
                  src={artist.image_url}
                  alt=""
                  className="relative size-40 rounded-full object-cover ring-2 ring-white/10"
                />
              ) : (
                <div className="relative grid size-40 place-items-center rounded-full bg-elevated text-4xl font-bold text-ink-2 ring-2 ring-white/10">
                  {artistInitials(artist.name)}
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="mb-3.5 flex flex-wrap gap-2">
                <Badge tone="warn">Artist</Badge>
                {artist.country ? <Badge tone="muted">{artist.country}</Badge> : null}
              </div>
              <h1 className="text-[clamp(32px,5.5vw,58px)] font-black leading-none tracking-[-0.03em] text-fg">
                {artist.name}
              </h1>
              {hasStats ? (
                <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
                  {artist.followers != null ? (
                    <StatChip label="followers">
                      {formatFollowers(artist.followers)}
                    </StatChip>
                  ) : null}
                  {popularity != null ? (
                    <StatChip label="popularity">{popularity}</StatChip>
                  ) : null}
                </div>
              ) : null}
              {genres.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {genres.slice(0, 5).map((g) => (
                    <span
                      key={g}
                      className="rounded-full border border-line-soft bg-elevated px-2.5 py-1 text-[11px] text-ink-2"
                    >
                      {g}
                    </span>
                  ))}
                  {genres.length > 5 ? (
                    <span className="rounded-full border border-line-soft bg-elevated px-2.5 py-1 text-[11px] text-muted">
                      +{genres.length - 5}
                    </span>
                  ) : null}
                </div>
              ) : null}
              {/* No Enqueue all: an artist is NOT a downloadable batch (Plan 8's
                  `unsupported_entity` rule). Enqueue is per-track / per-album. */}
              <div className="mt-5">
                <ActionButton
                  variant="ghost"
                  icon={<RefreshIcon className="size-4" />}
                  disabled={refreshing}
                  onClick={() => {
                    onRefresh();
                    toast.info("Refreshing from providers…");
                  }}
                >
                  {refreshing ? "Refreshing…" : "Refresh"}
                </ActionButton>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1080px] px-6 py-7">
        <div className="grid gap-8 lg:grid-cols-[1.9fr_1fr]">
          <div className="flex min-w-0 flex-col gap-8">
        <section className="flex flex-col gap-4">
          <SectionDivider
            title="Top tracks"
            accent="emerald"
            icon={<NoteIcon className="size-4" />}
          />
          {tracks.length === 0 ? (
            <EmptyState title="No tracks" description="No top tracks for this artist." />
          ) : (
            <TrackTable tracks={tracks} />
          )}
        </section>

        {albums.length > 0 ? <Discography albums={albums} downloading={submit.isPending} /> : null}
          </div>

          <aside className="flex min-w-0 flex-col gap-5">
            {bio ? (
              <Card title="About">
                <p className="text-[14px] leading-relaxed text-ink-2">{bio}</p>
              </Card>
            ) : null}
            <StatsCard id={artist.id} />
            <SourcesPanel entityType="artist" id={artist.id} />
          </aside>
        </div>
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
        accent="teal"
        count={albums.length}
        icon={<DiscIcon className="size-4" />}
      />
      {tabs.length > 1 ? (
        <div role="tablist" aria-label="Filter discography" className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={filter === tab.key}
              onClick={() => setFilter(tab.key)}
              className={`rounded-full border px-3 py-1 text-[12px] transition-colors ${
                filter === tab.key
                  ? "border-teal bg-teal/15 text-fg"
                  : "border-line-soft bg-elevated text-ink-2 hover:text-fg"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      ) : null}
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
