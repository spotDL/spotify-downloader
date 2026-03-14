import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAllLyrics,
  fetchAllLyrics,
  useSubmitLyrics,
  entityKeys,
} from "@/api/entities";
import {
  useLyrics,
  hasLyrics,
  toLyrics,
} from "@/api";
import { useAuthStore } from "@/stores/auth";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Button,
  Spinner,
  useToast,
} from "@/components/ui";
import { LyricsDisplay, MultiSourceLyricsDisplay } from "@/components/ui/lyrics-display";
import { SubmitLyricsModal } from "@/components/ui/submit-lyrics-modal";

interface SongLyricsSectionProps {
  songId: string;
  hasSong: boolean;
}

export function SongLyricsSection({ songId, hasSong }: SongLyricsSectionProps) {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const { success: showSuccess, error: showError } = useToast();

  const { data: lyricsData, isLoading: lyricsLoading } = useLyrics(songId, { enabled: hasSong });
  const { data: allLyricsData, isLoading: allLyricsLoading } = useAllLyrics(songId, { enabled: hasSong });
  const submitLyricsMutation = useSubmitLyrics();

  const [activeLyricsSource, setActiveLyricsSource] = useState<string | null>(null);
  const [fetchingAllLyrics, setFetchingAllLyrics] = useState(false);
  const [showSubmitLyrics, setShowSubmitLyrics] = useState(false);

  const lyrics = lyricsData && hasLyrics(lyricsData) ? toLyrics(lyricsData) : null;

  return (
    <>
      <Card variant="bordered" className="overflow-hidden">
        <CardHeader className="border-b border-zinc-800/50">
          <CardTitle className="flex items-center gap-2">
            <svg className="w-5 h-5 text-accent-cool" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Lyrics
            {allLyricsData && allLyricsData.lyrics.length > 1 && (
              <Badge variant="muted" size="sm">
                {allLyricsData.lyrics.length} sources
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isAuthenticated && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => setShowSubmitLyrics(true)}
              >
                Add Lyrics
              </Button>
            )}
            {hasSong && (
              <Button
                size="sm"
                variant="secondary"
                disabled={fetchingAllLyrics}
                onClick={async () => {
                  setFetchingAllLyrics(true);
                  try {
                    await fetchAllLyrics(songId);
                    queryClient.invalidateQueries({ queryKey: [...entityKeys.song(songId), "all-lyrics"] });
                    showSuccess("Fetched lyrics from all sources");
                  } catch {
                    showError("Failed to fetch lyrics");
                  } finally {
                    setFetchingAllLyrics(false);
                  }
                }}
              >
                {fetchingAllLyrics ? (
                  <Spinner size="sm" />
                ) : (
                  "Fetch All Sources"
                )}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {(lyricsLoading || allLyricsLoading) ? (
            <div className="flex items-center justify-center py-12">
              <Spinner size="md" />
            </div>
          ) : allLyricsData && allLyricsData.lyrics.length > 0 ? (
            <MultiSourceLyricsDisplay
              lyricsSources={allLyricsData.lyrics}
              activeSource={activeLyricsSource || undefined}
              onSourceChange={setActiveLyricsSource}
              maxHeight="400px"
            />
          ) : lyrics ? (
            <LyricsDisplay
              lyrics={lyrics}
              maxHeight="400px"
            />
          ) : (
            <div className="py-12 text-center">
              <p className="text-zinc-500">No lyrics available</p>
              <p className="text-sm text-zinc-600 mt-1">
                Lyrics couldn't be found for this track
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit Lyrics Modal */}
      <SubmitLyricsModal
        isOpen={showSubmitLyrics}
        onClose={() => setShowSubmitLyrics(false)}
        onSubmit={(data) => {
          submitLyricsMutation.mutate({ songId, ...data }, {
            onSuccess: () => setShowSubmitLyrics(false),
          });
        }}
        isSubmitting={submitLyricsMutation.isPending}
      />
    </>
  );
}
