import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  useFindMatchesMutation,
  useResolveSongMutation,
  useSearchAllPlatformsMutation,
  isValidUrl,
  type PlatformSearchResult,
} from "@/api";
import {
  Button,
  Input,
  Card,
  CardContent,
  Badge,
  PlatformBadge,
} from "@/components/ui";
import { features } from "@/config";
import { useQueueStore } from "@/stores/queue";
import type { Song, Match } from "@/types";

export const Route = createFileRoute("/")({
  component: HomePage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

// Platform configurations for visual distinction
const PLATFORM_CONFIG: Record<string, {
  gradient: string;
  glow: string;
  icon: React.ReactNode;
}> = {
  spotify: {
    gradient: "from-[#1db954] to-[#169c46]",
    glow: "shadow-[0_0_30px_-5px_rgba(29,185,84,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
      </svg>
    ),
  },
  apple_music: {
    gradient: "from-[#fc3c44] to-[#fa233b]",
    glow: "shadow-[0_0_30px_-5px_rgba(252,60,68,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.994 6.124a9.23 9.23 0 00-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043a5.022 5.022 0 00-1.877-.726 10.496 10.496 0 00-1.564-.15c-.04-.003-.083-.01-.124-.013H5.986c-.152.01-.303.017-.455.026-.747.043-1.49.123-2.193.4-1.336.53-2.3 1.452-2.865 2.78-.192.448-.292.925-.363 1.408-.056.392-.088.785-.1 1.18 0 .032-.007.062-.01.093v12.223c.01.14.017.283.027.424.05.815.154 1.624.497 2.373.65 1.42 1.738 2.353 3.234 2.801.42.127.856.187 1.293.228.555.053 1.11.06 1.667.06h11.03a12.5 12.5 0 001.57-.1c.822-.106 1.596-.35 2.296-.81a5.046 5.046 0 001.88-2.207c.186-.42.293-.87.37-1.324.113-.675.138-1.358.137-2.04-.002-3.8 0-7.595-.003-11.393zm-6.423 3.99v5.712c0 .417-.058.827-.244 1.206-.29.59-.76.962-1.388 1.14-.35.1-.706.157-1.07.173-.95.042-1.8-.228-2.403-.96-.63-.767-.608-1.917.038-2.65.555-.63 1.282-.9 2.105-.95.474-.03.946-.012 1.408-.145.238-.068.46-.165.56-.415.05-.12.075-.25.08-.382.01-.59.007-1.177.007-1.766V7.092c0-.29-.057-.348-.343-.298-.573.1-1.143.206-1.714.31l-3.474.63c-.027.005-.053.01-.08.018-.132.038-.193.117-.2.26-.007.073-.003.147-.003.22v8.095c0 .503-.02.998-.173 1.486-.226.716-.676 1.222-1.357 1.515-.25.108-.513.178-.78.22-.753.117-1.476.097-2.138-.31-.648-.397-1.028-.97-1.123-1.727-.074-.59.066-1.14.425-1.627.36-.487.854-.813 1.436-.98.337-.097.684-.14 1.033-.168.39-.03.78-.006 1.165-.088.347-.074.574-.284.645-.635.03-.148.04-.3.04-.45V5.626c0-.188.014-.375.078-.554.103-.29.343-.457.633-.516.166-.034.334-.06.503-.078.396-.043.794-.08 1.19-.12l2.06-.224 1.876-.21c.456-.05.91-.1 1.366-.154.09-.01.18-.015.268-.007.186.018.32.12.368.307.022.087.034.178.034.27l.002.858z"/>
      </svg>
    ),
  },
  deezer: {
    gradient: "from-[#a238ff] to-[#8519e0]",
    glow: "shadow-[0_0_30px_-5px_rgba(162,56,255,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.81 4.16v3.03H24V4.16h-5.19zM6.27 8.38v3.027h5.189V8.38H6.27zm12.54 0v3.027H24V8.38h-5.19zM6.27 12.594v3.027h5.189v-3.027H6.27zm6.271 0v3.027h5.19v-3.027h-5.19zm6.27 0v3.027H24v-3.027h-5.19zM0 16.81v3.029h5.19V16.81H0zm6.27 0v3.029h5.189V16.81H6.27zm6.271 0v3.029h5.19V16.81h-5.19zm6.27 0v3.029H24V16.81h-5.19z"/>
      </svg>
    ),
  },
  youtube_music: {
    gradient: "from-[#ff0000] to-[#cc0000]",
    glow: "shadow-[0_0_30px_-5px_rgba(255,0,0,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z"/>
      </svg>
    ),
  },
  soundcloud: {
    gradient: "from-[#ff5500] to-[#cc4400]",
    glow: "shadow-[0_0_30px_-5px_rgba(255,85,0,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M1.175 12.225c-.051 0-.094.046-.101.1l-.233 2.154.233 2.105c.007.058.05.098.101.098.05 0 .09-.04.099-.098l.255-2.105-.27-2.154c-.009-.06-.052-.1-.084-.1zm-.899.828c-.06 0-.091.037-.104.094L0 14.479l.165 1.308c.014.057.045.094.09.094s.089-.037.099-.094l.21-1.308-.21-1.334c-.01-.057-.054-.09-.09-.09zm1.83-1.229c-.06 0-.12.045-.12.104l-.21 2.563.225 2.458c0 .06.045.104.106.104.061 0 .12-.044.12-.104l.24-2.458-.24-2.563c0-.06-.059-.104-.12-.104zm.945-.089c-.075 0-.135.06-.15.135l-.193 2.64.21 2.544c.016.077.075.138.149.138.075 0 .135-.061.15-.138l.24-2.544-.24-2.64c-.015-.075-.074-.135-.166-.135zm1.155.36c-.005-.09-.075-.149-.159-.149-.09 0-.158.06-.164.149l-.217 2.43.2 2.563c0 .09.075.157.159.157.074 0 .148-.068.148-.158l.227-2.563-.194-2.43zm.809-1.709c-.101 0-.18.09-.18.181l-.21 3.957.227 2.563c0 .09.08.164.165.164.09 0 .164-.074.164-.164l.243-2.563-.239-3.957c0-.09-.075-.18-.18-.18zm1.065-.027c-.105 0-.195.09-.195.195l-.213 3.818.228 2.543c0 .105.09.18.18.18.104 0 .194-.075.194-.18l.24-2.543-.24-3.818c0-.105-.089-.195-.195-.195zm.872-.14c-.105 0-.21.09-.225.2l-.21 3.788.225 2.504c.015.12.12.209.239.209s.21-.089.225-.21l.24-2.504-.255-3.787c-.015-.111-.12-.2-.24-.2zm1.021-.166c-.12 0-.225.105-.225.225L7.5 14.479l.21 2.461c0 .119.105.225.225.225.119 0 .225-.105.225-.225l.225-2.461-.21-3.944c0-.12-.105-.225-.24-.225zm1.124-.153c-.135 0-.24.105-.24.24l-.181 3.927.196 2.43c0 .135.105.24.24.24.135 0 .24-.105.24-.24l.21-2.43-.21-3.927c0-.135-.105-.24-.255-.24zm1.095-.082c-.134 0-.254.105-.254.254l-.18 3.839.18 2.413c0 .135.12.254.255.254.135 0 .254-.12.254-.254l.196-2.413-.196-3.839c0-.15-.119-.254-.255-.254zm1.334-.252c-.148 0-.269.119-.269.269l-.165 3.822.18 2.383c0 .149.12.27.27.27.149 0 .269-.121.269-.27l.195-2.383-.195-3.822c0-.15-.12-.269-.285-.269zm1.006-.017c-.165 0-.285.12-.285.285l-.149 3.569.165 2.369c0 .165.12.3.285.3.166 0 .3-.135.3-.3l.165-2.369-.18-3.569c0-.165-.12-.285-.3-.285zm1.141-.172c-.18 0-.314.135-.33.315l-.135 3.588.15 2.323c.016.18.15.314.33.314.166 0 .315-.135.315-.314l.165-2.323-.18-3.588c0-.18-.135-.315-.315-.315zm1.216-.15c-.194 0-.344.149-.344.344l-.135 3.554.15 2.323c0 .194.149.344.344.344.194 0 .344-.15.344-.344l.165-2.323-.165-3.554c0-.194-.149-.344-.359-.344zm1.2.015c-.194 0-.36.165-.36.36l-.119 3.364.135 2.293c0 .194.165.36.36.36.194 0 .359-.165.359-.36l.165-2.293-.165-3.364c0-.194-.165-.36-.375-.36zm1.065-.2c-.209 0-.374.165-.389.374l-.12 3.42.135 2.263c.015.21.18.375.39.375.21 0 .375-.165.375-.375l.15-2.263-.165-3.42c0-.209-.165-.374-.375-.374zm2.024-.8c-.225 0-.405.18-.42.405l-.135 4.02.15 2.22c.015.239.195.42.42.42.224 0 .404-.181.404-.42l.166-2.22-.166-4.02c0-.225-.179-.405-.42-.405zm1.17.48c-.239 0-.435.194-.435.45l-.135 3.375.165 2.175c0 .254.196.45.45.45.254 0 .45-.196.45-.45l.165-2.175-.165-3.375c-.015-.256-.211-.45-.48-.45zm1.124.174c-.255 0-.465.21-.465.465l-.12 3.06.135 2.13c0 .255.21.48.465.48.255 0 .479-.225.479-.48l.165-2.13-.164-3.06c0-.255-.225-.465-.48-.465zm1.155.15c-.27 0-.495.225-.495.495l-.12 2.76.135 2.07c0 .27.225.495.495.495.27 0 .495-.225.495-.495l.15-2.07-.15-2.76c0-.27-.225-.495-.51-.495zm2.31-1.5c-.12-.045-.255-.074-.39-.074-.54 0-.99.449-.99 1.005v7.067c0 .554.45.994.99.994h3.344c1.854 0 3.36-1.5 3.36-3.36 0-1.86-1.506-3.36-3.36-3.36-.405 0-.795.075-1.155.21-.18-.69-.555-1.305-1.065-1.785z"/>
      </svg>
    ),
  },
  bandcamp: {
    gradient: "from-[#1da0c3] to-[#177a94]",
    glow: "shadow-[0_0_30px_-5px_rgba(29,160,195,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M0 18.75l7.437-13.5H24l-7.438 13.5H0z"/>
      </svg>
    ),
  },
  tidal: {
    gradient: "from-[#000000] to-[#333333]",
    glow: "shadow-[0_0_30px_-5px_rgba(0,0,0,0.5)]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.012 3.992L8.008 7.996 4.004 3.992 0 7.996l4.004 4.004 4.004-4.004 4.004 4.004-4.004 4.004 4.004 4.004 4.004-4.004-4.004-4.004 4.004-4.004-4.004-4.004zm7.988 0l-4.004 4.004 4.004 4.004 4.004-4.004z"/>
      </svg>
    ),
  },
};

// Animated gradient orb component
function GradientOrb({ className, delay = 0 }: { className?: string; delay?: number }) {
  return (
    <div
      className={`absolute rounded-full blur-[100px] opacity-30 animate-pulse ${className}`}
      style={{ animationDelay: `${delay}s`, animationDuration: "4s" }}
    />
  );
}

// Animated waveform background
function WaveformBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Gradient orbs */}
      <GradientOrb className="w-[600px] h-[600px] -top-48 -left-48 bg-emerald-500/40" delay={0} />
      <GradientOrb className="w-[500px] h-[500px] top-1/4 -right-32 bg-teal-500/30" delay={1} />
      <GradientOrb className="w-[400px] h-[400px] bottom-0 left-1/3 bg-cyan-500/25" delay={2} />

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:64px_64px]" />

      {/* Subtle radial gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,#0a0a0b_70%)]" />
    </div>
  );
}

function HomePage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [resolvedSong, setResolvedSong] = useState<Song | null>(null);
  const [platformResults, setPlatformResults] = useState<PlatformSearchResult[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [matchesSaved, setMatchesSaved] = useState(0);
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const resolveMutation = useResolveSongMutation();
  const searchAllMutation = useSearchAllPlatformsMutation();
  const findMatchesMutation = useFindMatchesMutation();

  const addToQueue = useQueueStore((state) => state.addItem);

  const handleDownload = (match: Match) => {
    if (!resolvedSong) return;
    addToQueue(resolvedSong, match);
    navigate({ to: "/queue" });
  };

  const isLoading =
    resolveMutation.isPending ||
    searchAllMutation.isPending ||
    findMatchesMutation.isPending;
  const error =
    resolveMutation.error || searchAllMutation.error || findMatchesMutation.error;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    setResolvedSong(null);
    setPlatformResults([]);
    setMatches([]);
    setMatchesSaved(0);

    try {
      // Check if input is a URL or a search query
      if (isValidUrl(query)) {
        // It's a URL - resolve it directly
        const response = await resolveMutation.mutateAsync(query);
        if (response.songs.length > 0) {
          setResolvedSong(response.songs[0]);

          // Find matches for the resolved song
          const matchResult = await findMatchesMutation.mutateAsync({
            sourceUrl: query,
            targetPlatforms: TARGET_PLATFORMS,
          });
          setMatches(matchResult.matches);
        }
      } else {
        // It's a search query - search all platforms
        const response = await searchAllMutation.mutateAsync({ query, limit: 10 });
        setPlatformResults(response.results);
        setMatchesSaved(response.matches_saved);
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
  };

  const handleSelectSong = async (song: Song) => {
    setResolvedSong(song);
    setPlatformResults([]);
    setMatches([]);

    try {
      const matchResult = await findMatchesMutation.mutateAsync({
        sourceUrl: song.url,
        targetPlatforms: TARGET_PLATFORMS,
      });
      setMatches(matchResult.matches);
    } catch (err) {
      console.error("Failed to find matches:", err);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const totalResults = platformResults.reduce((sum, r) => sum + r.total, 0);
  const activePlatforms = platformResults.filter((r) => r.total > 0);

  return (
    <div className="relative">
      {/* Background effects */}
      <WaveformBackground />

      <div className="relative z-10 space-y-12">
        {/* Hero Section */}
        <div className="text-center space-y-8 py-12">
          {/* Floating badge */}
          <div className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-gradient-to-r from-emerald-950/60 via-teal-950/60 to-cyan-950/60 border border-emerald-700/30 text-emerald-300 text-sm animate-slide-down backdrop-blur-sm">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-50" />
              <svg
                className="relative w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <span className="font-medium">Multi-platform music matching</span>
            <span className="w-px h-4 bg-emerald-700/50" />
            <span className="text-emerald-400/80 text-xs">Powered by community</span>
          </div>

          {/* Main headline */}
          <div className="space-y-4">
            <h1 className="text-5xl md:text-7xl font-black tracking-tighter animate-slide-up leading-[0.9]">
              <span className="block text-zinc-100">Download Music</span>
              <span className="block mt-2">
                <span className="text-zinc-100">from </span>
                <span className="relative">
                  <span className="gradient-text">Any Platform</span>
                  <svg className="absolute -bottom-2 left-0 w-full h-3 text-emerald-500/30" viewBox="0 0 100 12" preserveAspectRatio="none">
                    <path d="M0,8 Q25,0 50,8 T100,8" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
                  </svg>
                </span>
              </span>
            </h1>

            <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed animate-slide-up stagger-1">
              Search across <span className="text-zinc-200 font-medium">Spotify</span>,{" "}
              <span className="text-zinc-200 font-medium">YouTube Music</span>,{" "}
              <span className="text-zinc-200 font-medium">Deezer</span>, and more.
              <br className="hidden md:block" />
              We build a database of cross-platform matches together.
            </p>
          </div>

          {/* Platform icons row */}
          <div className="flex items-center justify-center gap-4 animate-slide-up stagger-2">
            {Object.entries(PLATFORM_CONFIG).slice(0, 6).map(([platform, config], index) => (
              <div
                key={platform}
                className={`w-10 h-10 rounded-xl bg-gradient-to-br ${config.gradient} flex items-center justify-center text-white/90 transition-all duration-300 hover:scale-110 hover:${config.glow}`}
                style={{ animationDelay: `${index * 0.1}s` }}
                title={platform.replace("_", " ")}
              >
                {config.icon}
              </div>
            ))}
          </div>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="max-w-3xl mx-auto animate-scale-in">
          <div className="relative group">
            {/* Animated glow effect */}
            <div className={`absolute -inset-1 bg-gradient-to-r from-emerald-500/30 via-teal-500/30 to-cyan-500/30 rounded-2xl blur-xl transition-all duration-500 ${isSearchFocused ? "opacity-100 scale-105" : "opacity-0 group-hover:opacity-70"}`} />

            {/* Search container */}
            <div className={`relative flex gap-3 p-2.5 bg-[#111113]/90 backdrop-blur-xl border rounded-2xl transition-all duration-300 ${isSearchFocused ? "border-emerald-700/50 shadow-lg shadow-emerald-900/20" : "border-zinc-800/80"}`}>
              {/* Search icon */}
              <div className="flex items-center pl-3">
                <svg
                  className={`w-5 h-5 transition-colors duration-200 ${isSearchFocused ? "text-emerald-400" : "text-zinc-500"}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>

              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setIsSearchFocused(false)}
                placeholder="Paste a song URL or search across all platforms..."
                className="flex-1 border-0 bg-transparent focus:ring-0 text-base placeholder:text-zinc-600"
              />

              <Button
                type="submit"
                isLoading={isLoading}
                disabled={!searchQuery.trim()}
                size="lg"
                className="px-6"
              >
                {isLoading ? (
                  "Searching..."
                ) : (
                  <>
                    Search All
                    <svg
                      className="w-4 h-4 ml-2"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M14 5l7 7m0 0l-7 7m7-7H3"
                      />
                    </svg>
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Search hints */}
          <div className="flex items-center justify-center gap-4 mt-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded bg-zinc-800/50 border border-zinc-700/50 font-mono text-zinc-400">spotify.com/track/...</kbd>
              <span>URLs</span>
            </span>
            <span className="w-px h-3 bg-zinc-700" />
            <span className="flex items-center gap-1.5">
              <span className="text-zinc-400">"artist name - song"</span>
              <span>Search</span>
            </span>
          </div>
        </form>

        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-6">
            <div className="relative">
              {/* Spinning ring */}
              <div className="w-16 h-16 rounded-full border-2 border-zinc-800 border-t-emerald-500 animate-spin" />
              {/* Inner pulsing circle */}
              <div className="absolute inset-3 rounded-full bg-gradient-to-br from-emerald-500/20 to-teal-500/20 animate-pulse" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-zinc-200 font-medium">Searching all platforms...</p>
              <p className="text-zinc-500 text-sm">This may take a few seconds</p>
            </div>
            {/* Platform loading indicators */}
            <div className="flex items-center gap-3">
              {Object.entries(PLATFORM_CONFIG).slice(0, 4).map(([platform, config], index) => (
                <div
                  key={platform}
                  className={`w-8 h-8 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center text-white/70 animate-pulse`}
                  style={{ animationDelay: `${index * 0.2}s` }}
                >
                  {config.icon}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <Card
            variant="bordered"
            className="max-w-2xl mx-auto border-red-900/50 glow-error"
          >
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-950/80 to-red-900/50 flex items-center justify-center shrink-0 border border-red-800/30">
                <svg
                  className="w-6 h-6 text-red-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-red-300">Search failed</p>
                <p className="text-sm text-zinc-400 mt-0.5">
                  {error instanceof Error ? error.message : "An error occurred"}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Multi-Platform Search Results */}
        {platformResults.length > 0 && !resolvedSong && !isLoading && (
          <div className="max-w-5xl mx-auto space-y-8">
            {/* Results Summary Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 bg-gradient-to-r from-zinc-900/80 via-zinc-900/50 to-zinc-900/80 rounded-2xl border border-zinc-800/50 backdrop-blur-sm">
              <div className="space-y-1">
                <h2 className="text-xl font-bold text-zinc-100">
                  Found {totalResults} results
                </h2>
                <p className="text-sm text-zinc-400">
                  Across {activePlatforms.length} platform{activePlatforms.length !== 1 ? "s" : ""}
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Platform mini badges */}
                <div className="flex items-center -space-x-1">
                  {activePlatforms.map((result) => {
                    const config = PLATFORM_CONFIG[result.platform];
                    return config ? (
                      <div
                        key={result.platform}
                        className={`w-7 h-7 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center text-white/80 border-2 border-zinc-900`}
                        title={result.platform_name}
                      >
                        <div className="scale-75">{config.icon}</div>
                      </div>
                    ) : null;
                  })}
                </div>

                {matchesSaved > 0 && (
                  <Badge variant="success" size="sm" className="animate-scale-in">
                    <svg
                      className="w-3.5 h-3.5 mr-1"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {matchesSaved} new matches saved
                  </Badge>
                )}
              </div>
            </div>

            {/* Results grouped by platform */}
            <div className="space-y-10">
              {platformResults.map((result, platformIndex) => {
                const config = PLATFORM_CONFIG[result.platform];

                return (
                  <div
                    key={result.platform}
                    className="animate-slide-up"
                    style={{ animationDelay: `${platformIndex * 0.1}s` }}
                  >
                    {/* Platform Header */}
                    <div className="flex items-center gap-4 mb-5">
                      {/* Platform badge with icon */}
                      <div className={`flex items-center gap-2.5 px-4 py-2.5 bg-gradient-to-r ${config?.gradient || "from-zinc-600 to-zinc-700"} rounded-xl text-white shadow-lg ${config?.glow || ""}`}>
                        {config?.icon && <span className="opacity-90">{config.icon}</span>}
                        <span className="font-semibold">{result.platform_name}</span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-sm text-zinc-400 font-medium">
                          {result.total} result{result.total !== 1 ? "s" : ""}
                        </span>

                        {result.error && (
                          <span className="inline-flex items-center gap-1.5 text-sm text-amber-400 bg-amber-950/30 px-3 py-1 rounded-lg border border-amber-800/30">
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                              />
                            </svg>
                            {result.error}
                          </span>
                        )}
                      </div>

                      {/* Decorative line */}
                      <div className="flex-1 h-px bg-gradient-to-r from-zinc-800 to-transparent" />
                    </div>

                    {/* Songs for this platform */}
                    {result.songs.length > 0 && (
                      <div className="grid gap-2">
                        {result.songs.map((song, songIndex) => (
                          <div
                            key={song.platform_id || songIndex}
                            onClick={() => handleSelectSong(song)}
                            className="group relative flex items-center gap-4 p-3 bg-zinc-900/50 hover:bg-zinc-800/70 border border-zinc-800/50 hover:border-zinc-700/50 rounded-xl cursor-pointer transition-all duration-200 hover:shadow-lg hover:shadow-black/20"
                          >
                            {/* Subtle gradient overlay on hover */}
                            <div className={`absolute inset-0 rounded-xl bg-gradient-to-r ${config?.gradient || "from-zinc-600 to-zinc-700"} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

                            {/* Album Art */}
                            <div className="relative w-14 h-14 shrink-0">
                              {song.cover_url ? (
                                <img
                                  src={song.cover_url}
                                  alt={song.name}
                                  className="w-14 h-14 rounded-lg object-cover shadow-md group-hover:shadow-lg transition-shadow duration-200"
                                />
                              ) : (
                                <div className={`w-14 h-14 rounded-lg bg-gradient-to-br ${config?.gradient || "from-zinc-700 to-zinc-800"} flex items-center justify-center shadow-md`}>
                                  <svg
                                    className="w-6 h-6 text-white/60"
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
                              )}
                              {/* Play overlay on hover */}
                              <div className="absolute inset-0 rounded-lg bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                                  <path d="M8 5v14l11-7z"/>
                                </svg>
                              </div>
                            </div>

                            {/* Song info */}
                            <div className="relative flex-1 min-w-0">
                              <h3 className="font-semibold text-zinc-100 truncate group-hover:text-white transition-colors">
                                {song.name}
                              </h3>
                              <p className="text-sm text-zinc-400 truncate">
                                {song.artists.join(", ")}
                              </p>
                            </div>

                            {/* Metadata */}
                            <div className="relative flex items-center gap-4">
                              {song.album_name && (
                                <span className="text-xs text-zinc-500 truncate max-w-[140px] hidden md:block px-2 py-1 rounded bg-zinc-800/50">
                                  {song.album_name}
                                </span>
                              )}
                              <span className="text-sm text-zinc-400 font-mono tabular-nums">
                                {formatDuration(song.duration)}
                              </span>
                              <svg
                                className="w-5 h-5 text-zinc-600 group-hover:text-zinc-400 group-hover:translate-x-0.5 transition-all duration-200"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M9 5l7 7-7 7"
                                />
                              </svg>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Song Result */}
        {resolvedSong && !isLoading && (
          <div className="max-w-3xl mx-auto animate-slide-up">
            {/* Selected song card */}
            <div className="relative p-6 bg-gradient-to-br from-zinc-900/90 via-zinc-900/80 to-zinc-900/90 rounded-2xl border border-zinc-800/50 shadow-2xl backdrop-blur-sm overflow-hidden">
              {/* Background glow effect */}
              <div className={`absolute -top-24 -right-24 w-64 h-64 rounded-full blur-3xl opacity-20 ${PLATFORM_CONFIG[resolvedSong.platform]?.gradient ? `bg-gradient-to-br ${PLATFORM_CONFIG[resolvedSong.platform]?.gradient}` : "bg-emerald-500"}`} />

              <div className="relative flex items-start gap-6">
                {/* Album Art */}
                <div className="relative w-28 h-28 shrink-0 group">
                  {resolvedSong.cover_url ? (
                    <img
                      src={resolvedSong.cover_url}
                      alt={resolvedSong.name}
                      className="w-28 h-28 rounded-xl object-cover shadow-2xl ring-1 ring-white/10"
                    />
                  ) : (
                    <div className={`w-28 h-28 rounded-xl bg-gradient-to-br ${PLATFORM_CONFIG[resolvedSong.platform]?.gradient || "from-zinc-700 to-zinc-800"} flex items-center justify-center shadow-2xl`}>
                      <svg
                        className="w-10 h-10 text-white/50"
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
                  )}
                  {/* Vinyl disc effect */}
                  <div className="absolute -right-4 top-1/2 -translate-y-1/2 w-20 h-20 rounded-full bg-gradient-to-br from-zinc-800 to-zinc-950 border border-zinc-700/50 opacity-80 group-hover:rotate-45 transition-transform duration-500">
                    <div className="absolute inset-3 rounded-full border border-zinc-600/30" />
                    <div className="absolute inset-6 rounded-full border border-zinc-600/20" />
                    <div className="absolute inset-[34px] rounded-full bg-emerald-500" />
                  </div>
                </div>

                <div className="flex-1 min-w-0 space-y-3">
                  <div>
                    <h3 className="text-2xl font-bold text-white truncate">
                      {resolvedSong.name}
                    </h3>
                    <p className="text-lg text-zinc-300 truncate mt-1">
                      {resolvedSong.artists.join(", ")}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap">
                    <PlatformBadge platform={resolvedSong.platform as any} />
                    {resolvedSong.album_name && (
                      <span className="text-sm text-zinc-400 px-2 py-1 bg-zinc-800/50 rounded-lg">
                        {resolvedSong.album_name}
                      </span>
                    )}
                    <span className="text-sm text-zinc-400 flex items-center gap-1.5 px-2 py-1 bg-zinc-800/50 rounded-lg">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      {formatDuration(resolvedSong.duration)}
                    </span>
                  </div>
                </div>

                {/* Back button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setResolvedSong(null);
                    setMatches([]);
                  }}
                  className="shrink-0"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Matches Results */}
        {matches.length > 0 && !isLoading && (
          <div className="max-w-3xl mx-auto space-y-6 mt-8">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <h2 className="text-xl font-bold text-zinc-100">
                  Found {matches.length} match{matches.length !== 1 ? "es" : ""}
                </h2>
                <p className="text-sm text-zinc-500">Select the best quality audio source</p>
              </div>
              <Badge variant="success" className="animate-pulse">
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Best quality
              </Badge>
            </div>

            <div className="space-y-3">
              {matches.map((match, index) => {
                const config = PLATFORM_CONFIG[match.target_platform];
                const isTop = index === 0;

                return (
                  <div
                    key={match.id}
                    className={`group relative p-4 rounded-xl border transition-all duration-200 animate-slide-up ${
                      isTop
                        ? "bg-gradient-to-br from-emerald-950/30 to-zinc-900/80 border-emerald-800/50 shadow-lg shadow-emerald-900/20"
                        : "bg-zinc-900/50 border-zinc-800/50 hover:bg-zinc-800/50 hover:border-zinc-700/50"
                    }`}
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    {/* Top match indicator */}
                    {isTop && (
                      <div className="absolute -top-2 right-4 px-2 py-0.5 bg-emerald-500 text-white text-xs font-semibold rounded-full shadow-lg">
                        Top Pick
                      </div>
                    )}

                    <div className="flex items-center justify-between gap-4">
                      {/* Match info */}
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <div className={`flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r ${config?.gradient || "from-zinc-600 to-zinc-700"} rounded-lg text-white text-sm font-medium`}>
                            {config?.icon && <span className="opacity-80 scale-90">{config.icon}</span>}
                            <span>{match.target_platform.replace("_", " ")}</span>
                          </div>
                          {match.match_type === "user" && (
                            <Badge variant="premium" size="sm">
                              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                              </svg>
                              User Verified
                            </Badge>
                          )}
                          {match.match_score !== null && (
                            <span className={`text-sm font-semibold ${match.match_score >= 90 ? "text-emerald-400" : match.match_score >= 70 ? "text-yellow-400" : "text-zinc-400"}`}>
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
                        <div className="flex items-center gap-1 text-sm bg-zinc-800/50 rounded-lg px-2 py-1">
                          <button className="p-1 hover:bg-zinc-700/50 rounded transition-colors">
                            <svg
                              className="w-4 h-4 text-emerald-400"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z"
                                clipRule="evenodd"
                              />
                            </svg>
                          </button>
                          <span className="font-medium text-zinc-300 min-w-[2ch] text-center">{match.upvotes - match.downvotes}</span>
                          <button className="p-1 hover:bg-zinc-700/50 rounded transition-colors">
                            <svg
                              className="w-4 h-4 text-red-400"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z"
                                clipRule="evenodd"
                              />
                            </svg>
                          </button>
                        </div>
                        {features.canDownload ? (
                          <Button
                            size="sm"
                            variant="primary"
                            className={isTop ? "shadow-emerald-500/30" : ""}
                            onClick={() => handleDownload(match)}
                          >
                            <svg
                              className="w-4 h-4 mr-1.5"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                              />
                            </svg>
                            Download
                          </Button>
                        ) : (
                          <a
                            href={match.target_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button size="sm" variant={isTop ? "primary" : "outline"}>
                              <svg
                                className="w-4 h-4 mr-1.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                />
                              </svg>
                              Open
                            </Button>
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !resolvedSong && platformResults.length === 0 && !error && (
          <div className="text-center py-20">
            {/* Animated vinyl stack */}
            <div className="relative w-32 h-32 mx-auto mb-8">
              {/* Background discs */}
              <div className="absolute top-2 left-2 w-28 h-28 rounded-full bg-zinc-800/80 border border-zinc-700/50" />
              <div className="absolute top-1 left-1 w-28 h-28 rounded-full bg-zinc-800/90 border border-zinc-700/50" />
              {/* Main disc */}
              <div className="relative w-28 h-28 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-900 border border-zinc-600/50 shadow-2xl">
                {/* Grooves */}
                <div className="absolute inset-3 rounded-full border border-zinc-600/30" />
                <div className="absolute inset-6 rounded-full border border-zinc-600/20" />
                <div className="absolute inset-9 rounded-full border border-zinc-600/20" />
                {/* Center label */}
                <div className="absolute inset-[38px] rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-zinc-900" />
                </div>
              </div>
              {/* Sparkle effects */}
              <div className="absolute -top-2 -right-2 w-4 h-4 text-emerald-400 animate-pulse">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/>
                </svg>
              </div>
              <div className="absolute bottom-4 -left-4 w-3 h-3 text-teal-400 animate-pulse" style={{ animationDelay: "0.5s" }}>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/>
                </svg>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xl text-zinc-200 font-semibold">
                Ready to find your music
              </p>
              <p className="text-zinc-400 max-w-md mx-auto">
                Search across all platforms to find and match music.
                We'll save cross-platform matches to build our community database.
              </p>
            </div>

            {/* Feature highlights */}
            <div className="flex items-center justify-center gap-6 mt-8 text-sm text-zinc-500">
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Multi-platform search
              </span>
              <span className="w-px h-4 bg-zinc-700" />
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Auto-save matches
              </span>
              <span className="w-px h-4 bg-zinc-700" />
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Community powered
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
