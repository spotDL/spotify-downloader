import type { ReactNode } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Disc3, RefreshCw } from "lucide-react";
import type { AlbumOut } from "../api/generated/types.gen";
import { useAlbum, useForceRefreshEntity } from "../api/queries";
import { isApiError } from "../api/errors";
import { ActionButton } from "../components/ActionButton";
import { Card, DetailRow } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { EnqueueAllButton } from "../components/EnqueueAllButton";
import { ErrorState } from "../components/ErrorState";
import { Feature } from "../components/Feature";
import { SourcesPanel } from "../components/SourcesPanel";
import { Spinner } from "../components/Spinner";
import { TrackTable } from "../components/TrackTable";
import { toast } from "../components/Toasts";

export const Route = createFileRoute("/albums/$albumId")({ component: AlbumPage });

/** `"ep"` → `"EP"`, `"album"` → `"Album"` — capitalize an album_type for display. */
function albumTypeLabel(type: string): string {
  const lower = type.toLowerCase();
  if (lower === "ep") return "EP";
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

// A mono, tabular fact in the hero strip: a faint label beside a bright value.
function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 font-mono text-xs tnum text-foreground">
      <span className="uppercase tracking-wider text-faint">{label}</span>
      {children}
    </span>
  );
}

function AlbumPage() {
  const { albumId } = Route.useParams();
  const query = useAlbum(albumId);

  if (query.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading album" className="size-8" />
      </div>
    );
  }
  if (query.isError) {
    return (
      <ErrorState
        description={
          isApiError(query.error) ? query.error.message : "Couldn't load this album."
        }
        action={
          <ActionButton variant="ghost" onClick={() => void query.refetch()}>
            Retry
          </ActionButton>
        }
      />
    );
  }

  const album = query.data;
  return <AlbumDetail album={album} />;
}

function AlbumDetail({ album }: { album: AlbumOut }) {
  // Force-refresh: re-resolves the album from its providers.
  const { refresh: onRefresh, refreshing } = useForceRefreshEntity("album", album.id);
  const tracks = album.tracks ?? [];
  const genres = album.genres ?? [];
  const typeLabel = album.album_type ? albumTypeLabel(album.album_type) : "Album";
  // Deezer-sourced albums can carry a raw fan-count in `popularity` (>100); only
  // render it as a 0–100 stat.
  const popularity =
    album.popularity != null && album.popularity >= 0 && album.popularity <= 100
      ? album.popularity
      : null;
  const hasDetails =
    Boolean(album.label) ||
    Boolean(album.copyright_text) ||
    Boolean(album.album_type) ||
    popularity != null;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-6 sm:flex-row sm:gap-7">
        <div className="size-40 shrink-0 overflow-hidden rounded-lg border border-border bg-elevated sm:size-48">
          {album.cover_url ? (
            <img src={album.cover_url} alt="" className="size-full object-cover" />
          ) : (
            <div className="grid size-full place-items-center text-faint">
              <Disc3 className="size-12" />
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-faint">
            {typeLabel}
          </p>
          <h1 className="mt-1.5 font-display text-3xl font-bold leading-tight tracking-tight text-foreground">
            {album.name}
          </h1>
          {album.album_artist ? (
            <p className="mt-2 font-medium text-foreground">{album.album_artist}</p>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
            {album.year ? <Fact label="year">{album.year}</Fact> : null}
            {album.track_count != null ? (
              <Fact label="tracks">{album.track_count}</Fact>
            ) : null}
          </div>
          {genres.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {genres.slice(0, 5).map((g) => (
                <span
                  key={g}
                  className="rounded-md border border-border bg-surface px-2.5 py-1 text-[11px] text-muted-foreground"
                >
                  {g}
                </span>
              ))}
              {genres.length > 5 ? (
                <span className="rounded-md border border-border bg-surface px-2.5 py-1 text-[11px] text-faint">
                  +{genres.length - 5}
                </span>
              ) : null}
            </div>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-2.5">
            {/* Albums are a downloadable batch → Enqueue all (bare canonical id;
                the server expands it into N jobs). */}
            <Feature flag="downloads">
              <EnqueueAllButton query={album.id} />
            </Feature>
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
          </div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.9fr_1fr]">
        <div className="min-w-0">
          {tracks.length === 0 ? (
            <EmptyState
              title="No tracks"
              description="This album has no listed tracks."
            />
          ) : (
            <TrackTable tracks={tracks} />
          )}
        </div>

        <aside className="flex min-w-0 flex-col gap-5">
          {hasDetails ? (
            <Card title="Details">
              {album.label ? (
                <DetailRow label="Label">{album.label}</DetailRow>
              ) : null}
              {album.album_type ? (
                <DetailRow label="Type">{typeLabel}</DetailRow>
              ) : null}
              {popularity != null ? (
                <DetailRow label="Popularity">{popularity} / 100</DetailRow>
              ) : null}
              {album.copyright_text ? (
                <DetailRow label="Copyright">{album.copyright_text}</DetailRow>
              ) : null}
            </Card>
          ) : null}
          <SourcesPanel entityType="album" id={album.id} />
        </aside>
      </div>
    </div>
  );
}
