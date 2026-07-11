import { Feature } from "./Feature";
import { DiscIcon, DownloadIcon } from "./icons";

// A cover-art album tile: a cover that opens the album, an optional year badge,
// and a hover-revealed download that enqueues the album batch (gated by the
// downloads feature). Shared by search results and the artist discography grid.
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
      <div className="relative aspect-square w-full overflow-hidden rounded-lg border border-border bg-elevated transition-colors group-hover:border-faint/50">
        <button type="button" aria-label={name} onClick={onOpen} className="absolute inset-0">
          {coverUrl ? (
            <img src={coverUrl} alt="" className="size-full object-cover" />
          ) : (
            <span className="grid size-full place-items-center text-faint">
              <DiscIcon className="size-8" />
            </span>
          )}
        </button>
        {year ? (
          <span className="pointer-events-none absolute left-1.5 top-1.5 rounded bg-background/70 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground tnum">
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
              className="absolute right-2 top-2 hidden size-9 place-items-center rounded-md bg-primary text-primary-foreground shadow-lg hover:bg-primary/85 group-hover:grid disabled:opacity-60"
            >
              <DownloadIcon className="size-4" />
            </button>
          </Feature>
        ) : null}
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-foreground">{name}</p>
      {subtitle ? <p className="truncate text-xs text-muted-foreground">{subtitle}</p> : null}
    </div>
  );
}
