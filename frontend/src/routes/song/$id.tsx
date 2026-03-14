import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo, useCallback } from "react";
import {
  useInternalSong,
  useRefreshEntity,
} from "@/api/entities";
import { useCreateReport } from "@/api";
import {
  Spinner,
  EntityErrorCard,
} from "@/components/ui";
import { ReportModal } from "@/components/ui/report-modal";
import {
  SongHeader,
  SongAudioFeatures,
  SongLyricsSection,
  SongMatchesSection,
  SongSnapshotsSection,
  SongMetadataPanel,
  buildDisplayMetadata,
} from "@/components/song";
import type { SnapshotInfo } from "@/components/song";
import type { CreateMetadataReportRequest } from "@/types";

export const Route = createFileRoute("/song/$id")({
  component: SongPage,
});

function SongPage() {
  const { id } = Route.useParams();
  const { data: song, isLoading, error } = useInternalSong(id);

  const createReportMutation = useCreateReport();
  const refreshMetadata = useRefreshEntity();

  const [showReportModal, setShowReportModal] = useState(false);
  const [showAllFeatures, setShowAllFeatures] = useState(false);
  const [snapshotInfo, setSnapshotInfo] = useState<SnapshotInfo | null>(null);

  const handleSnapshotChange = useCallback((info: SnapshotInfo) => {
    setSnapshotInfo(info);
  }, []);

  const displayMetadata = useMemo(() => {
    if (!song) return null;
    return buildDisplayMetadata(song, snapshotInfo);
  }, [song, snapshotInfo]);

  const handleReportSubmit = async (report: CreateMetadataReportRequest) => {
    await createReportMutation.mutateAsync(report);
  };

  const reportableFields = useMemo(() => {
    if (!song) return [];
    return [
      { name: "name", label: "Song Name", currentValue: song.name },
      { name: "artist", label: "Artist", currentValue: song.artist },
      { name: "album_name", label: "Album", currentValue: song.album_name || "" },
      { name: "year", label: "Year", currentValue: String(song.year || "") },
      { name: "release_date", label: "Release Date", currentValue: song.release_date || "" },
      { name: "label", label: "Record Label", currentValue: song.label || "" },
      { name: "genres", label: "Genres", currentValue: song.genres?.join(", ") || "" },
      { name: "isrc", label: "ISRC", currentValue: song.isrc || "" },
      { name: "track_number", label: "Track Number", currentValue: String(song.track_number || "") },
      { name: "disc_number", label: "Disc Number", currentValue: String(song.disc_number || "") },
    ];
  }, [song]);

  const handleRefresh = useCallback(async () => {
    await refreshMetadata.mutateAsync(id);
  }, [id, refreshMetadata]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading track...</p>
      </div>
    );
  }

  if (error || !song) {
    return <EntityErrorCard entityType="song" error={error ?? null} entityId={id} />;
  }

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Hero Section */}
      <SongHeader
        song={song}
        displayMetadata={displayMetadata}
        entityId={id}
        onRefresh={handleRefresh}
        onShowReportModal={() => setShowReportModal(true)}
      />

      {/* Multi-Source Metadata Controls & Comparison */}
      <SongSnapshotsSection
        songId={id}
        hasSong={!!song}
        onSnapshotChange={handleSnapshotChange}
      />

      {/* Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Matches & Lyrics */}
        <div className="lg:col-span-2 space-y-6">
          <SongMatchesSection songId={id} />
          <SongLyricsSection songId={id} hasSong={!!song} />
        </div>

        {/* Right Column - Metadata, Features & Links */}
        <div className="space-y-6">
          {/* Audio Features Panel */}
          {displayMetadata?.audio_features && (
            <SongAudioFeatures
              features={displayMetadata.audio_features}
              expanded={showAllFeatures}
              onToggleExpand={() => setShowAllFeatures(!showAllFeatures)}
            />
          )}

          {/* Metadata, Platform Links, Technical Info */}
          <SongMetadataPanel
            song={song}
            displayMetadata={displayMetadata}
            entityId={id}
            activeMetadataSource={snapshotInfo?.activeSource ?? null}
          />
        </div>
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onSubmit={handleReportSubmit}
        entityType="song"
        entityId={id}
        entityName={song.name}
        fields={reportableFields}
      />
    </div>
  );
}
