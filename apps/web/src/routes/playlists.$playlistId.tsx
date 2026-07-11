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
      <header className="flex flex-col gap-6 sm:flex-row sm:items-end">
        <div className="size-40 shrink-0 overflow-hidden rounded-lg border border-border bg-elevated sm:size-48">
          {playlist.cover_url ? (
            <img src={playlist.cover_url} alt="" className="size-full object-cover" />
          ) : (
            <div className="grid size-full place-items-center text-faint">
              <Music className="size-12" />
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-faint">Playlist</p>
          <h1 className="mt-1.5 font-display text-3xl font-bold tracking-tight text-foreground">
            {playlist.name}
          </h1>
          {playlist.owner ? (
            <p className="mt-2 text-sm font-medium text-foreground">{playlist.owner}</p>
          ) : null}

          <div className="mt-4 flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <StatChip label="tracks">{tracks.length}</StatChip>
          </div>

          {playlist.description ? (
            <p className="mt-3 max-w-[60ch] text-sm leading-relaxed text-muted-foreground">
              {playlist.description}
            </p>
          ) : null}

          <div className="mt-5 flex flex-wrap items-start gap-2.5">
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
        </div>
      </header>

      <section className="flex flex-col gap-4">
        <SectionDivider
          title="Tracks"
          count={tracks.length}
          icon={<Music className="size-4" />}
        />
        {tracks.length === 0 ? (
          <EmptyState title="No tracks" description="This playlist has no listed tracks." />
        ) : (
          <TrackTable tracks={tracks} />
        )}
      </section>
    </div>
  );
}
