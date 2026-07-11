import { createFileRoute } from "@tanstack/react-router";
import { Music, RefreshCw } from "lucide-react";
import type { PlaylistOut } from "../api/generated/types.gen";
import { useForceRefreshEntity, usePlaylist } from "../api/queries";
import { isApiError } from "../api/errors";
import { ActionButton } from "../components/ActionButton";
import { EmptyState } from "../components/EmptyState";
import { EnqueueAllButton } from "../components/EnqueueAllButton";
import { ErrorState } from "../components/ErrorState";
import { Feature } from "../components/Feature";
import { SectionDivider } from "../components/SectionDivider";
import { SourcesPanel } from "../components/SourcesPanel";
import { Spinner } from "../components/Spinner";
import { StatChip } from "../components/StatChip";
import { TrackTable } from "../components/TrackTable";
import { toast } from "../components/Toasts";

export const Route = createFileRoute("/playlists/$playlistId")({
  component: PlaylistPage,
});

function PlaylistPage() {
  const { playlistId } = Route.useParams();
  const query = usePlaylist(playlistId);

  if (query.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading playlist" className="size-8" />
      </div>
    );
  }
  if (query.isError) {
    return (
      <ErrorState
        description={
          isApiError(query.error) ? query.error.message : "Couldn't load this playlist."
        }
        action={
          <ActionButton variant="ghost" onClick={() => void query.refetch()}>
            Retry
          </ActionButton>
        }
      />
    );
  }

  return <PlaylistDetail playlist={query.data} />;
}

function PlaylistDetail({ playlist }: { playlist: PlaylistOut }) {
  // Force-refresh: re-resolves the playlist from its provider.
  const { refresh: onRefresh, refreshing } = useForceRefreshEntity("playlist", playlist.id);
  const tracks = playlist.tracks ?? [];

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-center gap-x-5 gap-y-4">
        <div className="size-28 shrink-0 overflow-hidden rounded-lg border border-border bg-elevated">
          {playlist.cover_url ? (
            <img src={playlist.cover_url} alt="" className="size-full object-cover" />
          ) : (
            <div className="grid size-full place-items-center text-faint">
              <Music className="size-10" />
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-faint">Playlist</p>
          <h1 className="mt-1 font-display text-2xl font-bold tracking-tight text-foreground">
            {playlist.name}
          </h1>
          {playlist.owner ? (
            <p className="mt-1 text-sm font-medium text-secondary">{playlist.owner}</p>
          ) : null}
          <div className="mt-2.5 flex flex-wrap items-baseline gap-x-5 gap-y-1.5">
            <StatChip label="tracks">{tracks.length}</StatChip>
          </div>

          {playlist.description ? (
            <p className="mt-3 max-w-[60ch] text-sm leading-relaxed text-muted-foreground">
              {playlist.description}
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2.5">
          {/* Playlists are a downloadable batch → Enqueue all (bare id). */}
          <Feature flag="downloads">
            <EnqueueAllButton query={playlist.id} />
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
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="flex min-w-0 flex-col gap-4">
          <SectionDivider title="Tracks" count={tracks.length} />
          {tracks.length === 0 ? (
            <EmptyState title="No tracks" description="This playlist has no listed tracks." />
          ) : (
            <TrackTable tracks={tracks} numbering="index" />
          )}
        </section>

        <aside className="flex min-w-0 flex-col gap-5 lg:sticky lg:top-20 lg:h-fit">
          <SourcesPanel entityType="playlist" id={playlist.id} />
        </aside>
      </div>
    </div>
  );
}
