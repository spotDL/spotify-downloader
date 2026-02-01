import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect, useCallback } from "react";
import { Button, Input, Card, CardContent, ConnectionStatusCompact } from "@/components/ui";
import { features, config } from "@/config";

export const Route = createFileRoute("/")({
  component: HomePage,
});

// ============================================================================
// LOCAL STORAGE UTILITIES
// ============================================================================

const RECENT_SEARCHES_KEY = "spotdl_recent_searches";
const MAX_RECENT_SEARCHES = 10;

interface RecentSearch {
  query: string;
  timestamp: number;
}

function getRecentSearches(): RecentSearch[] {
  try {
    const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function addRecentSearch(query: string): void {
  try {
    const searches = getRecentSearches();
    const filtered = searches.filter((s) => s.query.toLowerCase() !== query.toLowerCase());
    const updated = [
      { query, timestamp: Date.now() },
      ...filtered,
    ].slice(0, MAX_RECENT_SEARCHES);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
  } catch {
    // Silently fail
  }
}

function clearRecentSearches(): void {
  try {
    localStorage.removeItem(RECENT_SEARCHES_KEY);
  } catch {
    // Silently fail
  }
}

// ============================================================================
// MAIN HOME PAGE - Routes to correct variant
// ============================================================================

function HomePage() {
  if (features.isHosted) {
    return <HostedHomePage />;
  }
  return <SelfHostedHomePage />;
}

// ============================================================================
// HOSTED HOME PAGE - Open Source Project Landing
// ============================================================================

function HostedHomePage() {
  return (
    <div className="space-y-16 py-8">
      {/* Hero */}
      <div className="text-center space-y-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-zinc-800/50 text-zinc-400 text-sm">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          Open Source
        </div>

        <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
          <span className="text-[var(--accent-safe)]">spot</span>
          <span className="text-white">DL</span>
        </h1>

        <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
          Download music from Spotify, YouTube, SoundCloud, and more with metadata and lyrics.
          Free, open source, and community-driven.
        </p>

        <div className="flex items-center justify-center gap-4 pt-4">
          <a
            href={config.githubUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button size="lg" variant="primary">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
              </svg>
              View on GitHub
            </Button>
          </a>
          <a href="https://spotdl.readthedocs.io" target="_blank" rel="noopener noreferrer">
            <Button size="lg" variant="outline">
              Documentation
            </Button>
          </a>
        </div>
      </div>

      {/* Quick Install */}
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-6">
          <h3 className="text-lg font-semibold text-zinc-100 mb-4">Quick Install</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900 font-mono text-sm">
              <span className="text-zinc-500">$</span>
              <code className="text-zinc-100">pip install spotdl</code>
              <button
                className="ml-auto text-zinc-500 hover:text-zinc-300"
                onClick={() => navigator.clipboard.writeText("pip install spotdl")}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900 font-mono text-sm">
              <span className="text-zinc-500">$</span>
              <code className="text-zinc-100">spotdl download "artist - song"</code>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        <FeatureCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          }
          title="Multi-Platform"
          description="Download from Spotify, YouTube, YouTube Music, SoundCloud, and more."
        />
        <FeatureCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
          }
          title="Full Metadata"
          description="Automatically fetches album art, lyrics, artist info, and ID3 tags."
        />
        <FeatureCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          }
          title="Cross-Platform Matching"
          description="Intelligently matches songs across platforms using audio fingerprinting."
        />
      </div>

      {/* Supported Platforms */}
      <div className="text-center">
        <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wide mb-6">
          Supported Platforms
        </h3>
        <div className="flex items-center justify-center gap-6 flex-wrap">
          {["Spotify", "YouTube", "YouTube Music", "SoundCloud", "Bandcamp"].map((platform) => (
            <span key={platform} className="text-zinc-400 text-sm">
              {platform}
            </span>
          ))}
        </div>
      </div>

      {/* Connection Status */}
      <Card variant="bordered" className="max-w-3xl mx-auto">
        <CardContent className="py-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-zinc-300">Service Status</h4>
            <Link to="/settings" className="text-xs text-accent-needle hover:underline">
              View Details
            </Link>
          </div>
          <ConnectionStatusCompact />
        </CardContent>
      </Card>

      {/* Web UI Notice */}
      <Card variant="bordered" className="max-w-3xl mx-auto">
        <CardContent className="py-6 text-center">
          <h3 className="text-lg font-semibold text-zinc-100 mb-2">
            This is the SpotDL Matching Service
          </h3>
          <p className="text-zinc-400 mb-4">
            A crowdsourced database of cross-platform song matches.
            To download music, install spotDL locally or self-host this web interface.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/search">
              <Button variant="primary">Browse Matches</Button>
            </Link>
            <Link to="/matching">
              <Button variant="outline">Contribute</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// SELF-HOSTED HOME PAGE - Immediate Action Interface
// ============================================================================

function SelfHostedHomePage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);

  useEffect(() => {
    setRecentSearches(getRecentSearches());
  }, []);

  const handleSearch = useCallback((e?: React.FormEvent, query?: string) => {
    if (e) e.preventDefault();
    const searchTerm = (query || searchQuery).trim();
    if (!searchTerm) return;

    addRecentSearch(searchTerm);
    navigate({ to: "/search", search: { q: searchTerm } });
  }, [searchQuery, navigate]);

  const handleClearRecent = () => {
    clearRecentSearches();
    setRecentSearches([]);
  };

  return (
    <div className="space-y-8">
      {/* Search Section */}
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-zinc-100 mb-2">
            Search & Download Music
          </h1>
          <p className="text-zinc-400">
            Paste a URL or search for songs, albums, artists, or playlists
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch}>
          <div className="flex gap-3">
            <div className="relative flex-1">
              <svg
                className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500"
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
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="spotify.com/track/... or artist - song name"
                className="pl-12 py-3 text-base"
              />
            </div>
            <Button type="submit" size="lg" disabled={!searchQuery.trim()}>
              Search
            </Button>
          </div>
        </form>

        {/* Input hints */}
        <div className="flex items-center justify-center gap-6 text-xs text-zinc-500">
          <span>Spotify URL</span>
          <span className="w-1 h-1 rounded-full bg-zinc-700" />
          <span>YouTube URL</span>
          <span className="w-1 h-1 rounded-full bg-zinc-700" />
          <span>Artist - Song</span>
          <span className="w-1 h-1 rounded-full bg-zinc-700" />
          <span>Album name</span>
        </div>
      </div>

      {/* Recent Searches */}
      {recentSearches.length > 0 && (
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-zinc-400">Recent Searches</h3>
            <button
              onClick={handleClearRecent}
              className="text-xs text-zinc-500 hover:text-zinc-300"
            >
              Clear
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {recentSearches.slice(0, 8).map((search, i) => (
              <button
                key={i}
                onClick={() => handleSearch(undefined, search.query)}
                className="px-3 py-1.5 rounded-lg bg-zinc-800/50 text-sm text-zinc-300 hover:bg-zinc-700/50 transition-colors"
              >
                {search.query}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
        <QuickAction
          to="/queue"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          }
          label="Download Queue"
        />
        <QuickAction
          to="/matching"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          }
          label="Find Matches"
        />
        <QuickAction
          to="/settings"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          }
          label="Settings"
        />
        <a href={config.githubUrl} target="_blank" rel="noopener noreferrer" className="block">
          <div className="flex flex-col items-center gap-2 p-4 rounded-xl bg-zinc-800/30 hover:bg-zinc-800/50 transition-colors text-zinc-400 hover:text-zinc-200">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
            </svg>
            <span className="text-sm font-medium">GitHub</span>
          </div>
        </a>
      </div>

      {/* Connection Status */}
      <Card variant="bordered" className="max-w-3xl mx-auto">
        <CardContent className="py-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-zinc-300">Service Status</h4>
            <Link to="/settings" className="text-xs text-accent-needle hover:underline">
              View Details
            </Link>
          </div>
          <ConnectionStatusCompact />
        </CardContent>
      </Card>

      {/* Tips */}
      <Card variant="bordered" className="max-w-3xl mx-auto">
        <CardContent className="py-4">
          <h4 className="text-sm font-medium text-zinc-300 mb-3">Tips</h4>
          <ul className="space-y-2 text-sm text-zinc-400">
            <li className="flex items-start gap-2">
              <span className="text-[var(--accent-safe)]">•</span>
              Paste Spotify, YouTube, or SoundCloud URLs directly
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--accent-safe)]">•</span>
              Search by "Artist - Song" for best results
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--accent-safe)]">•</span>
              Use the matching page to find cross-platform equivalents
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// SHARED COMPONENTS
// ============================================================================

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Card variant="bordered">
      <CardContent className="py-6">
        <div className="w-12 h-12 rounded-xl bg-[var(--accent-safe)]/10 flex items-center justify-center mb-4 text-[var(--accent-safe)]">
          {icon}
        </div>
        <h3 className="font-semibold text-zinc-100 mb-2">{title}</h3>
        <p className="text-sm text-zinc-400">{description}</p>
      </CardContent>
    </Card>
  );
}

function QuickAction({
  to,
  icon,
  label,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link to={to}>
      <div className="flex flex-col items-center gap-2 p-4 rounded-xl bg-zinc-800/30 hover:bg-zinc-800/50 transition-colors text-zinc-400 hover:text-zinc-200">
        {icon}
        <span className="text-sm font-medium">{label}</span>
      </div>
    </Link>
  );
}
