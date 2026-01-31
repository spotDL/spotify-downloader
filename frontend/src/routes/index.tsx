import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useFindMatchesMutation, useResolveSongMutation } from "@/api";
import { Button, Input, Card, CardContent, Badge, Loading, PlatformBadge } from "@/components/ui";
import type { Song, Match } from "@/types";

export const Route = createFileRoute("/")({
  component: HomePage,
});

const PLATFORMS = [
  { id: "spotify", name: "Spotify", color: "from-[#1db954] to-[#169c46]" },
  { id: "apple_music", name: "Apple Music", color: "from-[#fc3c44] to-[#fa233b]" },
  { id: "deezer", name: "Deezer", color: "from-[#a238ff] to-[#8519e0]" },
  { id: "youtube_music", name: "YouTube Music", color: "from-[#ff0000] to-[#cc0000]" },
  { id: "soundcloud", name: "SoundCloud", color: "from-[#ff5500] to-[#cc4400]" },
  { id: "bandcamp", name: "Bandcamp", color: "from-[#1da0c3] to-[#177a94]" },
] as const;

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
      const song = await resolveMutation.mutateAsync(searchQuery.trim());
      setResolvedSong(song);

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
    <div className="space-y-12">
      {/* Hero Section */}
      <div className="text-center space-y-6 py-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-950/30 border border-emerald-800/30 text-emerald-400 text-sm animate-slide-down">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Multi-platform music matching
        </div>

        <h1 className="text-5xl md:text-6xl font-bold tracking-tight animate-slide-up">
          Download Music from{" "}
          <span className="gradient-text">Any Platform</span>
        </h1>

        <p className="text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed animate-slide-up stagger-1">
          Enter a song URL from Spotify, Apple Music, Deezer, or any supported platform
          to find and download the best audio match.
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="max-w-2xl mx-auto animate-scale-in">
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/20 via-teal-500/20 to-cyan-500/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <div className="relative flex gap-3 p-2 bg-[#111113] border border-zinc-800 rounded-2xl">
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Paste a song URL or search..."
              className="flex-1 border-0 bg-transparent focus:ring-0 text-base"
            />
            <Button
              type="submit"
              isLoading={isLoading}
              disabled={!searchQuery.trim()}
              size="lg"
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Search
            </Button>
          </div>
        </div>
      </form>

      {/* Platform Badges */}
      <div className="flex flex-wrap justify-center gap-3 max-w-3xl mx-auto">
        {PLATFORMS.map((platform, index) => (
          <div
            key={platform.id}
            className={`px-4 py-2 bg-gradient-to-r ${platform.color} rounded-xl text-sm font-semibold text-white shadow-lg opacity-0 animate-scale-in`}
            style={{ animationDelay: `${index * 0.05 + 0.2}s`, animationFillMode: "forwards" }}
          >
            {platform.name}
          </div>
        ))}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Loading text="Searching for matches..." variant="waveform" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50 glow-error">
          <CardContent className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-950/50 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-red-400">Search failed</p>
              <p className="text-sm text-zinc-400">
                {error instanceof Error ? error.message : "An error occurred"}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Song Result */}
      {resolvedSong && !isLoading && (
        <Card variant="bordered" className="max-w-2xl mx-auto animate-slide-up glow">
          <CardContent className="space-y-4">
            <div className="flex items-start gap-5">
              {/* Album Art / Vinyl */}
              <div className="relative w-20 h-20 shrink-0">
                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-zinc-700 to-zinc-900 shadow-xl" />
                <div className="absolute inset-2 rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-emerald-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                    />
                  </svg>
                </div>
              </div>

              <div className="flex-1 min-w-0 space-y-2">
                <h3 className="text-xl font-semibold text-zinc-50 truncate">
                  {resolvedSong.name}
                </h3>
                <p className="text-zinc-400 truncate">
                  {resolvedSong.artists.join(", ")}
                </p>
                <div className="flex items-center gap-3 flex-wrap">
                  <PlatformBadge platform={resolvedSong.platform as any} />
                  {resolvedSong.album_name && (
                    <span className="text-sm text-zinc-500">
                      {resolvedSong.album_name}
                    </span>
                  )}
                  <span className="text-sm text-zinc-500 flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
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
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-zinc-100">
              Found {matches.length} match{matches.length !== 1 ? "es" : ""}
            </h2>
            <Badge variant="success">Best quality</Badge>
          </div>

          <div className="space-y-3">
            {matches.map((match, index) => (
              <Card
                key={match.id}
                variant="bordered"
                hover
                className="animate-slide-up"
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <CardContent>
                  <div className="flex items-center justify-between gap-4">
                    {/* Match info */}
                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <PlatformBadge platform={match.target_platform as any} />
                        {match.match_type === "user" && (
                          <Badge variant="premium" size="sm">User Verified</Badge>
                        )}
                        {match.match_score !== null && (
                          <span className="text-sm font-medium text-emerald-400">
                            {Math.round(match.match_score)}% match
                          </span>
                        )}
                      </div>
                      <a
                        href={match.target_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-zinc-400 hover:text-zinc-200 truncate block transition-colors"
                      >
                        {match.target_url}
                      </a>
                    </div>

                    {/* Votes and actions */}
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="flex items-center gap-1 text-emerald-400">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                          </svg>
                          {match.upvotes}
                        </span>
                        <span className="flex items-center gap-1 text-red-400">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          {match.downvotes}
                        </span>
                      </div>
                      <Button size="sm" variant="primary">
                        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
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
        <div className="text-center py-16">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-zinc-800/50 flex items-center justify-center">
            <svg className="w-10 h-10 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <p className="text-zinc-400 text-lg">
            Enter a song URL above to find download matches
          </p>
          <p className="text-zinc-500 text-sm mt-2">
            Supports Spotify, Apple Music, Deezer, YouTube Music, and more
          </p>
        </div>
      )}
    </div>
  );
}
