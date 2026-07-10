import { Feature } from "./Feature";
import { DiscIcon, DownloadIcon } from "./icons";

// A cover-art album tile (mockup `.album`): a hover-lifting cover that opens the
// album, an optional year badge, and a hover-revealed download that enqueues the
// album batch (gated by the downloads feature). Shared by search results and the
// artist discography grid.
export function AlbumGridCard({
  name,
  coverUrl,
  year,
  subtitle,
  onOpen,
  onDownload,
  downloading = false,
}: {
  name: string;
  coverUrl?: string | null;
  year?: number | null;
  subtitle?: string | null;
  onOpen: () => void;
  onDownload?: () => void;
  downloading?: boolean;
}) {
  return (
    <div className="group flex flex-col">
      <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-elevated ring-1 ring-white/5 transition-transform group-hover:-translate-y-1">
        <button type="button" aria-label={name} onClick={onOpen} className="absolute inset-0">
          {coverUrl ? (
            <img src={coverUrl} alt="" className="size-full object-cover" />
          ) : (
            <span className="grid size-full place-items-center text-muted">
              <DiscIcon className="size-8" />
            </span>
          )}
        </button>
        {year ? (
          <span className="pointer-events-none absolute left-1.5 top-1.5 rounded bg-void/70 px-1.5 py-0.5 font-mono text-[10px] text-ink-2">
            {year}
          </span>
        ) : null}
        {onDownload ? (
          <Feature flag="downloads">
            <button
              type="button"
              aria-label={`Download ${name}`}
              disabled={downloading}
              onClick={onDownload}
              className="absolute right-2 top-2 hidden size-9 place-items-center rounded-full bg-emerald text-void shadow-card hover:brightness-110 group-hover:grid disabled:opacity-60"
            >
              <DownloadIcon className="size-4" />
            </button>
          </Feature>
        ) : null}
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-fg">{name}</p>
      {subtitle ? <p className="truncate text-xs text-muted">{subtitle}</p> : null}
    </div>
  );
}
