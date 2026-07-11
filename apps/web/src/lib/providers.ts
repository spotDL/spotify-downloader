// Provider display metadata + canonical URL builders. Kept UI-agnostic (a plain
// lib, not a component) so PlatformLinks, the match rows, and the command
// palette all read one table. `dotClass` maps to a palette token (index.css).

type ProviderMeta = { label: string; dotClass: string };

const PROVIDER_META: Record<string, ProviderMeta> = {
  spotify: { label: "Spotify", dotClass: "bg-spotify" },
  deezer: { label: "Deezer", dotClass: "bg-deezer" },
  itunes: { label: "Apple Music", dotClass: "bg-apple" },
  ytmusic: { label: "YouTube Music", dotClass: "bg-youtube" },
  youtube: { label: "YouTube", dotClass: "bg-youtube" },
  soundcloud: { label: "SoundCloud", dotClass: "bg-soundcloud" },
  bandcamp: { label: "Bandcamp", dotClass: "bg-info" },
  piped: { label: "Piped", dotClass: "bg-youtube" },
  musicbrainz: { label: "MusicBrainz", dotClass: "bg-musicbrainz" },
  lastfm: { label: "Last.fm", dotClass: "bg-destructive" },
  genius: { label: "Genius", dotClass: "bg-warning" },
  musixmatch: { label: "Musixmatch", dotClass: "bg-info" },
  lrclib: { label: "LRCLIB", dotClass: "bg-success" },
  azlyrics: { label: "AZLyrics", dotClass: "bg-faint" },
};

/** Human label + accent-dot class for a provider id (falls back gracefully). */
export function providerMeta(provider: string): ProviderMeta {
  return (
    PROVIDER_META[provider] ?? {
      label: provider.charAt(0).toUpperCase() + provider.slice(1),
      dotClass: "bg-faint",
    }
  );
}

/**
 * Best-effort canonical "listen on" URL for a track on a metadata provider.
 * Returns `null` when we can't build a stable public URL (e.g. iTunes needs a
 * storefront) so the caller can omit the link rather than emit a dead one.
 */
export function trackProviderUrl(
  provider: string | null | undefined,
  providerId: string | null | undefined,
): string | null {
  if (!provider || !providerId) return null;
  switch (provider) {
    case "spotify":
      return `https://open.spotify.com/track/${providerId}`;
    case "deezer":
      return `https://www.deezer.com/track/${providerId}`;
    case "ytmusic":
      return `https://music.youtube.com/watch?v=${providerId}`;
    case "youtube":
    case "piped":
      return `https://www.youtube.com/watch?v=${providerId}`;
    case "musicbrainz":
      return `https://musicbrainz.org/recording/${providerId}`;
    case "soundcloud":
      // SoundCloud ids are numeric API ids without a public slug — no URL.
      return null;
    default:
      return null;
  }
}
