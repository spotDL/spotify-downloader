import { providerMeta } from "../lib/providers";
import { ExternalIcon } from "./icons";

export type PlatformLink = { provider: string; url: string };

// The "Listen on" panel rows: an accent dot, the provider name, and an
// open-in-new affordance. Renders nothing when there are no links, so a
// track/artist with no public URLs omits the panel gracefully.
export function PlatformLinks({ links }: { links: PlatformLink[] }) {
  if (links.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {links.map((link) => {
        const meta = providerMeta(link.provider);
        return (
          <a
            key={`${link.provider}:${link.url}`}
            href={link.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2.5 transition-colors hover:bg-elevated"
          >
            <span className={`size-2.5 rounded-full ${meta.dotClass}`} aria-hidden />
            <span className="text-sm text-foreground">{meta.label}</span>
            <span className="ml-auto flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
              open
              <ExternalIcon className="size-3" />
            </span>
          </a>
        );
      })}
    </div>
  );
}
