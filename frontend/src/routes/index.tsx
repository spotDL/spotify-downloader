import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useFindMatchesMutation, useResolveSongMutation } from "@/api";
import { Button, Input, Card, CardContent, Badge, Loading } from "@/components/ui";
import type { Song, Match } from "@/types";

export const Route = createFileRoute("/")({
  component: HomePage,
});

const PLATFORMS = [
  { id: "spotify", name: "Spotify", color: "bg-green-600" },
  { id: "apple_music", name: "Apple Music", color: "bg-pink-600" },
  { id: "deezer", name: "Deezer", color: "bg-purple-600" },
  { id: "youtube_music", name: "YouTube Music", color: "bg-red-600" },
  { id: "soundcloud", name: "SoundCloud", color: "bg-orange-600" },
  { id: "bandcamp", name: "Bandcamp", color: "bg-cyan-600" },
];

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [resolvedSong, setResolvedSong] = useState<Song | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);

  const resolveMutation = useResolveSongMutation();
  const findMatchesMutation = useFindMatchesMutation();

  const isLoading = resolveMutation.isPending || findMatchesMutation.isPending;
  const error = resolveMutation.error || findMatchesMutation.error;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setResolvedSong(null);
    setMatches([]);

    try {
      // First resolve the URL to get song metadata
      const song = await resolveMutation.mutateAsync(searchQuery.trim());
      setResolvedSong(song);

      // Then find matches on target platforms
      const result = await findMatchesMutation.mutateAsync({
        sourceUrl: searchQuery.trim(),
        targetPlatforms: TARGET_PLATFORMS,
      });
      setMatches(result.matches);
    } catch (err) {
      console.error("Search failed:", err);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">
          Download Music from{" "}
          <span className="text-green-500">Any Platform</span>
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto">
          Enter a song URL from Spotify, Apple Music, Deezer, YouTube Music, or
          any supported platform to find and download the best audio match.
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
        <div className="flex gap-2">
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Paste a song URL or search..."
            className="flex-1"
          />
          <Button type="submit" isLoading={isLoading} disabled={!searchQuery.trim()}>
            Search
          </Button>
        </div>
      </form>

      {/* Platform Badges */}
      <div className="flex flex-wrap justify-center gap-2 max-w-2xl mx-auto">
        {PLATFORMS.map((platform) => (
          <div
            key={platform.id}
            className={`px-3 py-1.5 ${platform.color} rounded-full text-xs font-medium text-white`}
          >
            {platform.name}
          </div>
        ))}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-8">
          <Loading text="Searching for matches..." />
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card variant="bordered" className="max-w-2xl mx-auto border-red-700">
          <CardContent>
            <p className="text-red-400">
              {error instanceof Error ? error.message : "An error occurred"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Song Result */}
      {resolvedSong && !isLoading && (
        <Card variant="bordered" className="max-w-2xl mx-auto">
          <CardContent className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 bg-gray-700 rounded-lg flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-gray-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                  />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-gray-100 truncate">
                  {resolvedSong.name}
                </h3>
                <p className="text-gray-400 truncate">
                  {resolvedSong.artists.join(", ")}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="info">{resolvedSong.platform}</Badge>
                  {resolvedSong.album_name && (
                    <span className="text-sm text-gray-500">
                      {resolvedSong.album_name}
                    </span>
                  )}
                  <span className="text-sm text-gray-500">
                    {formatDuration(resolvedSong.duration_seconds)}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Matches Results */}
      {matches.length > 0 && !isLoading && (
        <div className="max-w-2xl mx-auto space-y-4">
          <h2 className="text-xl font-semibold text-gray-100">
            Found {matches.length} match{matches.length !== 1 ? "es" : ""}
          </h2>

          <div className="space-y-3">
            {matches.map((match) => (
              <Card key={match.id} variant="bordered" className="hover:border-gray-600 transition-colors">
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={match.match_type === "user" ? "success" : "default"}
                        >
                          {match.target_platform}
                        </Badge>
                        {match.match_score !== null && (
                          <span className="text-sm text-gray-400">
                            {Math.round(match.match_score)}% match
                          </span>
                        )}
                      </div>
                      <a
                        href={match.target_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-400 hover:text-blue-300 truncate block mt-1"
                      >
                        {match.target_url}
                      </a>
                    </div>
                    <div className="flex items-center gap-4 ml-4">
                      <div className="flex items-center gap-1 text-sm">
                        <span className="text-green-500">▲ {match.upvotes}</span>
                        <span className="text-red-500">▼ {match.downvotes}</span>
                      </div>
                      <Button size="sm" variant="outline">
                        Download
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !resolvedSong && !error && (
        <div className="text-center py-8">
          <p className="text-gray-500">
            Enter a song URL above to find download matches
          </p>
        </div>
      )}
    </div>
  );
}
