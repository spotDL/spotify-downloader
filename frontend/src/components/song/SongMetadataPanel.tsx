import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui";
import { MetadataPanel, MetadataField } from "@/components/ui/metadata-source-badge";
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import type { EnhancedSong } from "@/types";

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

interface SongMetadataPanelProps {
  song: EnhancedSong;
  displayMetadata: EnhancedSong | null;
  entityId: string;
  activeMetadataSource: string | null;
}

export function SongMetadataPanel({
  song,
  displayMetadata,
  entityId,
  activeMetadataSource,
}: SongMetadataPanelProps) {
  const [showTechnicalMetadata, setShowTechnicalMetadata] = useState(false);

  const platformsForGrid = song.platforms;

  return (
    <div className="space-y-6">
      {/* Platform Links */}
      {platformsForGrid.length > 0 && (
        <Card variant="bordered">
          <CardHeader className="border-b border-zinc-800/50">
            <CardTitle className="text-base">Listen On</CardTitle>
          </CardHeader>
          <CardContent>
            <PlatformLinksGrid platforms={platformsForGrid} />
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <MetadataPanel
        title="Track Details"
        defaultOpen={true}
      >
        <div className="space-y-3">
          <MetadataField label="Title" value={displayMetadata?.name || song.name} />
          <MetadataField label="Artist" value={displayMetadata?.artist || song.artist} />
          {(displayMetadata?.album_name || song.album_name) && (
            <MetadataField label="Album" value={displayMetadata?.album_name || song.album_name || ""} />
          )}
          <MetadataField label="Duration" value={<span className="font-mono">{formatDuration(song.duration)}</span>} />
          {(displayMetadata?.release_date || song.release_date) && (
            <MetadataField label="Release Date" value={displayMetadata?.release_date || song.release_date || ""} />
          )}
          {!(displayMetadata?.release_date || song.release_date) && (displayMetadata?.year || song.year) && (
            <MetadataField label="Year" value={String(displayMetadata?.year || song.year)} />
          )}
          {(displayMetadata?.label || song.label) && (
            <MetadataField label="Label" value={displayMetadata?.label || song.label || ""} />
          )}
          {((displayMetadata?.genres && displayMetadata.genres.length > 0) || (song.genres && song.genres.length > 0)) && (
            <MetadataField
              label="Genres"
              value={(displayMetadata?.genres || song.genres)?.join(", ") || ""}
            />
          )}
          {song.popularity !== null && song.popularity !== undefined && (
            <MetadataField label="Popularity" value={`${song.popularity}%`} />
          )}
          {/* Show source indicator when viewing non-primary source */}
          {activeMetadataSource && activeMetadataSource !== "spotify" && (
            <div className="pt-2 mt-2 border-t border-zinc-800/30">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wide">
                Data from <span className="text-accent-cool">{activeMetadataSource}</span>
              </p>
            </div>
          )}
        </div>
      </MetadataPanel>

      {/* Copyright & Label Info */}
      {(displayMetadata?.label || song.label || song.copyright_text) && (
        <Card variant="bordered">
          <CardHeader className="border-b border-zinc-800/50">
            <CardTitle className="text-base flex items-center gap-2">
              <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Rights Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(displayMetadata?.label || song.label) && (
              <div>
                <span className="text-xs text-zinc-500 uppercase tracking-wide">Label</span>
                <p className="text-sm text-zinc-300 mt-0.5">{displayMetadata?.label || song.label}</p>
              </div>
            )}
            {song.copyright_text && (
              <div>
                <span className="text-xs text-zinc-500 uppercase tracking-wide">Copyright</span>
                <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{song.copyright_text}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Technical Metadata */}
      <Card variant="bordered">
        <CardHeader
          className="border-b border-zinc-800/50 cursor-pointer hover:bg-zinc-800/20 transition-colors"
          onClick={() => setShowTechnicalMetadata(!showTechnicalMetadata)}
        >
          <div className="flex items-center justify-between w-full">
            <CardTitle className="text-base flex items-center gap-2">
              <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              Technical Info
            </CardTitle>
            <svg
              className={`w-5 h-5 text-zinc-500 transition-transform ${showTechnicalMetadata ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </CardHeader>
        {showTechnicalMetadata && (
          <CardContent className="space-y-3">
            {song.isrc && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-500">ISRC</span>
                <code className="text-sm font-mono text-accent-cool bg-bg-panel px-2 py-1 rounded">
                  {song.isrc}
                </code>
              </div>
            )}
            {platformsForGrid.map((p) => (
              <div key={p.platform} className="flex items-center justify-between mt-1">
                <span className="text-sm text-zinc-500">
                  {p.platform} ID
                </span>
                <code className="text-sm font-mono text-zinc-400 bg-bg-panel px-2 py-1 rounded truncate max-w-[180px]">
                  {p.platform_id}
                </code>
              </div>
            ))}
            <div className="flex items-center justify-between mt-2">
              <span className="text-sm text-zinc-500">Internal ID</span>
              <code className="text-sm font-mono text-zinc-500 bg-bg-panel px-2 py-1 rounded truncate max-w-[180px]">
                {entityId}
              </code>
            </div>

            {/* External IDs */}
            {(song.musicbrainz_id || song.discogs_id) && (
              <div className="pt-3 mt-3 border-t border-zinc-800/50">
                <p className="text-xs text-zinc-500 uppercase tracking-wide mb-2">External IDs</p>
                {song.musicbrainz_id && (
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-zinc-500">MusicBrainz</span>
                    <a
                      href={`https://musicbrainz.org/recording/${song.musicbrainz_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-mono text-orange-400 hover:text-orange-300 bg-bg-panel px-2 py-1 rounded truncate max-w-[180px]"
                    >
                      {song.musicbrainz_id.slice(0, 8)}...
                    </a>
                  </div>
                )}
                {song.discogs_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-500">Discogs</span>
                    <a
                      href={`https://www.discogs.com/release/${song.discogs_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-mono text-zinc-400 hover:text-zinc-300 bg-bg-panel px-2 py-1 rounded"
                    >
                      {song.discogs_id}
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* Field Sources */}
            {song.field_sources && Object.keys(song.field_sources).length > 0 && (
              <div className="pt-3 mt-3 border-t border-zinc-800/50">
                <p className="text-xs text-zinc-500 uppercase tracking-wide mb-2">Data Sources</p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(song.field_sources).map(([field, source]) => (
                    <span
                      key={field}
                      className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400"
                      title={`${field} from ${source}`}
                    >
                      {field}: <span className="text-accent-cool">{source as string}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Enriched timestamp */}
            {song.enriched_at && (
              <div className="flex items-center justify-between pt-2">
                <span className="text-sm text-zinc-500">Last Enriched</span>
                <span className="text-xs text-zinc-500">
                  {new Date(song.enriched_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
