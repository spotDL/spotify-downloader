import { createFileRoute } from "@tanstack/react-router";
import type { AlbumOut } from "../api/generated/types.gen";
import { useAlbum } from "../api/queries";
import { isApiError } from "../api/errors";
import { joinMeta } from "../lib/format";
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
import { DiscIcon, RefreshIcon } from "../components/icons";
import { toast } from "../components/Toasts";

export const Route = createFileRoute("/albums/$albumId")({ component: AlbumPage });

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
      <div className="mx-auto max-w-[1080px] px-6 py-16">
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
      </div>
    );
  }

  const album = query.data;
  return <AlbumDetail album={album} onRefresh={() => void query.refetch()} />;
}

function AlbumDetail({
  album,
  onRefresh,
}: {
  album: AlbumOut;
  onRefresh: () => void;
}) {
  const tracks = album.tracks ?? [];
  const meta = joinMeta([
    album.year,
    album.track_count != null ? `${album.track_count} tracks` : null,
  ]);

  return (
    <div>
      <div className="grain relative overflow-hidden border-b border-line-soft">
        <HeroBackdrop coverUrl={album.cover_url} />
        <div className="relative z-[2] mx-auto max-w-[1080px] px-6">
          <div className="flex flex-col gap-6 pt-9 pb-7 sm:flex-row sm:items-end sm:gap-7">
            <div className="size-40 shrink-0 overflow-hidden rounded-[14px] shadow-[0_24px_60px_-18px_#000] ring-1 ring-white/10 sm:size-[196px]">
              {album.cover_url ? (
                <img src={album.cover_url} alt="" className="size-full object-cover" />
              ) : (
                <div className="grid size-full place-items-center bg-elevated text-ink-4">
                  <DiscIcon className="size-12" />
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="mb-3.5 flex flex-wrap gap-2">
                <Badge tone="brand">Album</Badge>
              </div>
              <h1 className="text-[clamp(28px,4.5vw,48px)] font-black leading-none tracking-[-0.03em] text-fg">
                {album.name}
              </h1>
              {album.album_artist ? (
                <p className="mt-2.5 text-[17px] font-semibold text-fg">
                  {album.album_artist}
                </p>
              ) : null}
              {meta ? (
                <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
                  {album.year ? <StatChip label="year">{album.year}</StatChip> : null}
                  {album.track_count != null ? (
                    <StatChip label="tracks">{album.track_count}</StatChip>
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
                  icon={<RefreshIcon className="size-4" />}
                  onClick={() => {
                    onRefresh();
                    toast.info("Refreshing…");
                  }}
                >
                  Refresh
                </ActionButton>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1080px] px-6 py-7">
        {tracks.length === 0 ? (
          <EmptyState title="No tracks" description="This album has no listed tracks." />
        ) : (
          <TrackTable tracks={tracks} />
        )}
      </div>
    </div>
  );
}
