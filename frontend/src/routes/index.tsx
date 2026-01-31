import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button, Input } from "@/components/ui";

export const Route = createFileRoute("/")({
  component: HomePage,
});

// Platform configurations for visual display
const PLATFORM_CONFIG: Record<string, {
  gradient: string;
  icon: React.ReactNode;
}> = {
  spotify: {
    gradient: "from-[#1db954] to-[#169c46]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
      </svg>
    ),
  },
  deezer: {
    gradient: "from-[#a238ff] to-[#8519e0]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.81 4.16v3.03H24V4.16h-5.19zM6.27 8.38v3.027h5.189V8.38H6.27zm12.54 0v3.027H24V8.38h-5.19zM6.27 12.594v3.027h5.189v-3.027H6.27zm6.271 0v3.027h5.19v-3.027h-5.19zm6.27 0v3.027H24v-3.027h-5.19zM0 16.81v3.029h5.19V16.81H0zm6.27 0v3.029h5.189V16.81H6.27zm6.271 0v3.029h5.19V16.81h-5.19zm6.27 0v3.029H24V16.81h-5.19z"/>
      </svg>
    ),
  },
  youtube_music: {
    gradient: "from-[#ff0000] to-[#cc0000]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z"/>
      </svg>
    ),
  },
  soundcloud: {
    gradient: "from-[#ff5500] to-[#cc4400]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M1.175 12.225c-.051 0-.094.046-.101.1l-.233 2.154.233 2.105c.007.058.05.098.101.098.05 0 .09-.04.099-.098l.255-2.105-.27-2.154c-.009-.06-.052-.1-.084-.1zm-.899.828c-.06 0-.091.037-.104.094L0 14.479l.165 1.308c.014.057.045.094.09.094s.089-.037.099-.094l.21-1.308-.21-1.334c-.01-.057-.054-.09-.09-.09zm1.83-1.229c-.06 0-.12.045-.12.104l-.21 2.563.225 2.458c0 .06.045.104.106.104.061 0 .12-.044.12-.104l.24-2.458-.24-2.563c0-.06-.059-.104-.12-.104zm.945-.089c-.075 0-.135.06-.15.135l-.193 2.64.21 2.544c.016.077.075.138.149.138.075 0 .135-.061.15-.138l.24-2.544-.24-2.64c-.015-.075-.074-.135-.166-.135z"/>
      </svg>
    ),
  },
  apple_music: {
    gradient: "from-[#fc3c44] to-[#fa233b]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.994 6.124a9.23 9.23 0 00-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043a5.022 5.022 0 00-1.877-.726 10.496 10.496 0 00-1.564-.15c-.04-.003-.083-.01-.124-.013H5.986c-.152.01-.303.017-.455.026-.747.043-1.49.123-2.193.4-1.336.53-2.3 1.452-2.865 2.78-.192.448-.292.925-.363 1.408-.056.392-.088.785-.1 1.18 0 .032-.007.062-.01.093v12.223c.01.14.017.283.027.424.05.815.154 1.624.497 2.373.65 1.42 1.738 2.353 3.234 2.801.42.127.856.187 1.293.228.555.053 1.11.06 1.667.06h11.03a12.5 12.5 0 001.57-.1c.822-.106 1.596-.35 2.296-.81a5.046 5.046 0 001.88-2.207c.186-.42.293-.87.37-1.324.113-.675.138-1.358.137-2.04-.002-3.8 0-7.595-.003-11.393z"/>
      </svg>
    ),
  },
  tidal: {
    gradient: "from-[#000000] to-[#333333]",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.012 3.992L8.008 7.996 4.004 3.992 0 7.996l4.004 4.004 4.004-4.004 4.004 4.004-4.004 4.004 4.004 4.004 4.004-4.004-4.004-4.004 4.004-4.004-4.004-4.004zm7.988 0l-4.004 4.004 4.004 4.004 4.004-4.004z"/>
      </svg>
    ),
  },
};

function GradientOrb({ className, delay = 0 }: { className?: string; delay?: number }) {
  return (
    <div
      className={`absolute rounded-full blur-[100px] opacity-30 animate-pulse ${className}`}
      style={{ animationDelay: `${delay}s`, animationDuration: "4s" }}
    />
  );
}

function WaveformBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <GradientOrb className="w-[600px] h-[600px] -top-48 -left-48 bg-emerald-500/40" delay={0} />
      <GradientOrb className="w-[500px] h-[500px] top-1/4 -right-32 bg-teal-500/30" delay={1} />
      <GradientOrb className="w-[400px] h-[400px] bottom-0 left-1/3 bg-cyan-500/25" delay={2} />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:64px_64px]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,#0a0a0b_70%)]" />
    </div>
  );
}

function HomePage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    // Redirect to search page with query
    navigate({ to: "/search", search: { q: query } });
  };

  return (
    <div className="relative min-h-[calc(100vh-200px)]">
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
                className={`w-10 h-10 rounded-xl bg-gradient-to-br ${config.gradient} flex items-center justify-center text-white/90 transition-all duration-300 hover:scale-110`}
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
                disabled={!searchQuery.trim()}
                size="lg"
                className="px-6"
              >
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

        {/* Features section */}
        <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6 pt-8">
          <div className="p-6 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="font-semibold text-zinc-100 mb-2">Universal Search</h3>
            <p className="text-sm text-zinc-400">
              Search once across Spotify, YouTube Music, Deezer, SoundCloud, and more simultaneously.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
            <div className="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            </div>
            <h3 className="font-semibold text-zinc-100 mb-2">Cross-Platform Matching</h3>
            <p className="text-sm text-zinc-400">
              Find the same song across different platforms automatically with our community-driven database.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <h3 className="font-semibold text-zinc-100 mb-2">Download Queue</h3>
            <p className="text-sm text-zinc-400">
              Add songs to your download queue and manage downloads from a single interface.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
