import { createFileRoute } from "@tanstack/react-router";
import type { PlaylistOut } from "../api/generated/types.gen";
import { useForceRefreshEntity, usePlaylist } from "../api/queries";
import { isApiError } from "../api/errors";
import { ActionButton } from "../components/ActionButton";
import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { EnqueueAllButton } from "../components/EnqueueAllButton";
import { ErrorState } from "../components/ErrorState";
import { Feature } from "../components/Feature";
import { HeroBackdrop } from "../components/HeroBackdrop";
import { Spinner } from "../components/Spinner";
import { StatChip } from "../components/StatChip";
import { TrackTable } from "../components/TrackTable";
import { NoteIcon, RefreshIcon } from "../components/icons";
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
      <div className="mx-auto max-w-[1080px] px-6 py-16">
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
      </div>
    );
  }

  return <PlaylistDetail playlist={query.data} />;
}

function PlaylistDetail({ playlist }: { playlist: PlaylistOut }) {
  // Force-refresh: re-resolves the playlist from its provider.
  const { refresh: onRefresh, refreshing } = useForceRefreshEntity("playlist", playlist.id);
  const tracks = playlist.tracks ?? [];

  return (
    <div>
      <div className="grain relative overflow-hidden border-b border-line-soft">
        <HeroBackdrop coverUrl={playlist.cover_url} />
        <div className="relative z-[2] mx-auto max-w-[1080px] px-6">
          <div className="flex flex-col gap-6 pt-9 pb-7 sm:flex-row sm:items-end sm:gap-7">
            <div className="size-40 shrink-0 overflow-hidden rounded-[14px] shadow-[0_24px_60px_-18px_#000] ring-1 ring-white/10 sm:size-[196px]">
              {playlist.cover_url ? (
                <img src={playlist.cover_url} alt="" className="size-full object-cover" />
              ) : (
                <div className="grid size-full place-items-center bg-elevated text-ink-4">
                  <NoteIcon className="size-12" />
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="mb-3.5 flex flex-wrap gap-2">
                <Badge tone="brand">Playlist</Badge>
              </div>
              <h1 className="text-[clamp(28px,4.5vw,48px)] font-black leading-none tracking-[-0.03em] text-fg">
                {playlist.name}
              </h1>
              {playlist.owner ? (
                <p className="mt-2.5 text-[17px] font-semibold text-fg">{playlist.owner}</p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
                <StatChip label="tracks">{tracks.length}</StatChip>
              </div>
              {playlist.description ? (
                <p className="mt-3 max-w-[60ch] text-sm leading-relaxed text-ink-2">
                  {playlist.description}
                </p>
              ) : null}
              <div className="mt-5 flex flex-wrap gap-2.5">
                {/* Playlists are a downloadable batch → Enqueue all (bare id). */}
                <Feature flag="downloads">
                  <EnqueueAllButton query={playlist.id} />
                </Feature>
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
        {tracks.length === 0 ? (
          <EmptyState
            title="No tracks"
            description="This playlist has no listed tracks."
          />
        ) : (
          <TrackTable tracks={tracks} />
        )}
      </div>
    </div>
  );
}
