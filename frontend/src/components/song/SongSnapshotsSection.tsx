import { useState, useMemo, useEffect } from "react";
import {
  useMetadataSnapshots,
} from "@/api/entities";
import {
  Card,
  CardContent,
  Button,
} from "@/components/ui";
import { MetadataSourceSelector } from "@/components/ui/metadata-source-selector";
import { MetadataComparisonTable } from "@/components/ui/metadata-comparison";
import type { EnhancedSong, NormalizedMetadata } from "@/types";
import type { MetadataSnapshot } from "@/types/metadata";

interface SongSnapshotsSectionProps {
  songId: string;
  hasSong: boolean;
  /** Callback to notify parent of the active snapshot for display metadata merging */
  onSnapshotChange?: (snapshot: SnapshotInfo) => void;
}

export interface SnapshotInfo {
  activeSource: string | null;
  activeSnapshot: {
    source: string;
    confidence: number;
    data: NormalizedMetadata;
    fetched_at?: string;
    fetchedAt?: string;
  } | null;
  snapshots: MetadataSnapshot[];
  sources: string[];
}

export function SongSnapshotsSection({ songId, hasSong, onSnapshotChange }: SongSnapshotsSectionProps) {
  const [activeMetadataSource, setActiveMetadataSource] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  const { data: snapshotsData } = useMetadataSnapshots(songId, {
    enabled: hasSong,
  });

  // Set default source when snapshots load
  useEffect(() => {
    if (snapshotsData?.snapshots?.length && !activeMetadataSource) {
      const sorted = [...snapshotsData.snapshots].sort((a, b) => b.confidence - a.confidence);
      setActiveMetadataSource(sorted[0].source);
    }
  }, [snapshotsData, activeMetadataSource]);

  const extendedSnapshotsInfo = useMemo(() => {
    const backendSnapshots = snapshotsData?.snapshots || [];
    const allSources = Array.from(new Set([
      ...(snapshotsData?.sources || []),
    ]));

    return {
      snapshots: backendSnapshots,
      sources: allSources,
    };
  }, [snapshotsData]);

  const activeSnapshot = useMemo(() => {
    if (!activeMetadataSource) return extendedSnapshotsInfo.snapshots[0] || null;
    return extendedSnapshotsInfo.snapshots.find((s) => s.source === activeMetadataSource) || null;
  }, [extendedSnapshotsInfo, activeMetadataSource]);

  // Notify parent when snapshot state changes
  useEffect(() => {
    onSnapshotChange?.({
      activeSource: activeMetadataSource,
      activeSnapshot: activeSnapshot as SnapshotInfo["activeSnapshot"],
      snapshots: extendedSnapshotsInfo.snapshots,
      sources: extendedSnapshotsInfo.sources,
    });
  }, [activeMetadataSource, activeSnapshot, extendedSnapshotsInfo, onSnapshotChange]);

  if (!extendedSnapshotsInfo.snapshots.length) {
    return null;
  }

  return (
    <>
      {/* Multi-Source Metadata Controls */}
      <Card variant="bordered" className="overflow-hidden">
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            {/* Source Selector */}
            <MetadataSourceSelector
              sources={extendedSnapshotsInfo.sources}
              activeSource={activeMetadataSource || ""}
              onSourceChange={setActiveMetadataSource}
              snapshots={extendedSnapshotsInfo.snapshots as any}
              showConfidence={true}
              size="md"
            />

            {/* Compare Sources Button */}
            {extendedSnapshotsInfo.snapshots.length > 1 && (
              <Button
                variant={showComparison ? "primary" : "outline"}
                size="sm"
                onClick={() => setShowComparison(!showComparison)}
              >
                <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
                {showComparison ? "Hide Comparison" : "Compare Sources"}
              </Button>
            )}
          </div>

          {/* Active Source Info */}
          {activeSnapshot && (
            <div className="mt-3 pt-3 border-t border-zinc-800/50 flex items-center gap-2 text-xs text-zinc-500">
              <span>Viewing data from</span>
              <span className="font-medium text-zinc-300">{activeMetadataSource}</span>
              <span>•</span>
              <span>Confidence: {Math.round(activeSnapshot.confidence * 100)}%</span>
              <span>•</span>
              <span>Fetched: {new Date((activeSnapshot as any).fetched_at || (activeSnapshot as any).fetchedAt || new Date()).toLocaleDateString()}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Metadata Comparison Table */}
      {showComparison && extendedSnapshotsInfo.snapshots.length > 1 && (
        <MetadataComparisonTable
          snapshots={extendedSnapshotsInfo.snapshots as any}
          showOnlyDifferences={false}
          className="animate-slide-up"
        />
      )}
    </>
  );
}

/**
 * Build display metadata by merging the active snapshot data with the song.
 */
export function buildDisplayMetadata(
  song: EnhancedSong,
  snapshotInfo: SnapshotInfo | null,
): EnhancedSong {
  if (!snapshotInfo?.activeSnapshot?.data) return song;

  const data = snapshotInfo.activeSnapshot.data;

  return {
    ...song,
    name: data.name || song.name,
    artist: data.album_artist || (data.artists?.[0]) || song.artist,
    album_name: data.album_name || song.album_name,
    genres: data.genres || song.genres,
    label: data.label || song.label,
    release_date: data.release_date || song.release_date,
    year: data.year || song.year,
    audio_features: song.audio_features
      ? {
          ...song.audio_features,
          bpm: data.bpm ?? song.audio_features.bpm,
          energy: data.energy ?? song.audio_features.energy,
          danceability: data.danceability ?? song.audio_features.danceability,
          valence: data.valence ?? song.audio_features.valence,
        }
      : song.audio_features,
  };
}
