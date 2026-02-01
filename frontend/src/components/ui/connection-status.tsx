import { useState, useEffect } from "react";
import { clsx } from "clsx";
import { Badge } from "./badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./card";
import { Spinner } from "./spinner";

// ============================================================================
// TYPES
// ============================================================================

export type ConnectionState = "connected" | "connecting" | "disconnected" | "error";

export interface ServiceStatus {
  name: string;
  displayName: string;
  state: ConnectionState;
  latency?: number; // ms
  error?: string;
  icon?: React.ReactNode;
}

// ============================================================================
// MOCK DATA & HOOKS - Replace with real API calls when available
// ============================================================================

const PLATFORMS = [
  { name: "spotify", displayName: "Spotify", category: "source" },
  { name: "deezer", displayName: "Deezer", category: "source" },
  { name: "apple_music", displayName: "Apple Music", category: "source" },
  { name: "youtube_music", displayName: "YouTube Music", category: "source" },
  { name: "youtube", displayName: "YouTube", category: "target" },
  { name: "soundcloud", displayName: "SoundCloud", category: "target" },
  { name: "bandcamp", displayName: "Bandcamp", category: "target" },
];

const METADATA_SOURCES = [
  { name: "musicbrainz", displayName: "MusicBrainz", category: "metadata" },
  { name: "genius", displayName: "Genius (Lyrics)", category: "metadata" },
  { name: "musixmatch", displayName: "Musixmatch (Lyrics)", category: "metadata" },
];

function useServiceStatus(): { services: ServiceStatus[]; isLoading: boolean; refetch: () => void } {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const checkServices = async () => {
    setIsLoading(true);

    // Simulate checking each service
    const allServices = [...PLATFORMS, ...METADATA_SOURCES];
    const results: ServiceStatus[] = [];

    for (const service of allServices) {
      // Simulate random latency and occasional failures
      const isConnected = Math.random() > 0.15;
      const latency = isConnected ? Math.floor(Math.random() * 200) + 50 : undefined;

      results.push({
        name: service.name,
        displayName: service.displayName,
        state: isConnected ? "connected" : "error",
        latency,
        error: isConnected ? undefined : "Service unavailable",
      });
    }

    setServices(results);
    setIsLoading(false);
  };

  useEffect(() => {
    checkServices();
    // Refresh every 60 seconds
    const interval = setInterval(checkServices, 60000);
    return () => clearInterval(interval);
  }, []);

  return { services, isLoading, refetch: checkServices };
}

// ============================================================================
// STATUS INDICATOR - Single status dot with animation
// ============================================================================

function StatusDot({ state, size = "sm" }: { state: ConnectionState; size?: "xs" | "sm" | "md" }) {
  const sizeClasses = {
    xs: "w-1.5 h-1.5",
    sm: "w-2 h-2",
    md: "w-3 h-3",
  };

  const colorClasses = {
    connected: "bg-emerald-500",
    connecting: "bg-amber-500",
    disconnected: "bg-zinc-500",
    error: "bg-red-500",
  };

  return (
    <div className="relative">
      <div className={clsx(sizeClasses[size], "rounded-full", colorClasses[state])} />
      {(state === "connected" || state === "connecting") && (
        <div
          className={clsx(
            sizeClasses[size],
            "rounded-full absolute inset-0 animate-ping opacity-50",
            colorClasses[state]
          )}
        />
      )}
    </div>
  );
}

// ============================================================================
// COMPACT CONNECTION STATUS - For home page
// ============================================================================

export function ConnectionStatusCompact({ className }: { className?: string }) {
  const { services, isLoading } = useServiceStatus();

  const sources = services.filter(s =>
    PLATFORMS.some(p => p.name === s.name && p.category === "source")
  );
  const targets = services.filter(s =>
    PLATFORMS.some(p => p.name === s.name && p.category === "target")
  );
  const metadata = services.filter(s =>
    METADATA_SOURCES.some(m => m.name === s.name)
  );

  const connectedSources = sources.filter(s => s.state === "connected").length;
  const connectedTargets = targets.filter(s => s.state === "connected").length;
  const connectedMetadata = metadata.filter(s => s.state === "connected").length;

  if (isLoading) {
    return (
      <div className={clsx("flex items-center gap-2 text-sm text-zinc-500", className)}>
        <Spinner size="sm" />
        <span>Checking connections...</span>
      </div>
    );
  }

  return (
    <div className={clsx("flex items-center gap-4", className)}>
      {/* Sources */}
      <div className="flex items-center gap-2">
        <StatusDot state={connectedSources === sources.length ? "connected" : connectedSources > 0 ? "connecting" : "error"} />
        <span className="text-xs text-zinc-400">
          <span className="font-medium text-zinc-300">{connectedSources}/{sources.length}</span> Sources
        </span>
      </div>

      <div className="w-px h-4 bg-zinc-800" />

      {/* Targets */}
      <div className="flex items-center gap-2">
        <StatusDot state={connectedTargets === targets.length ? "connected" : connectedTargets > 0 ? "connecting" : "error"} />
        <span className="text-xs text-zinc-400">
          <span className="font-medium text-zinc-300">{connectedTargets}/{targets.length}</span> Targets
        </span>
      </div>

      <div className="w-px h-4 bg-zinc-800" />

      {/* Metadata */}
      <div className="flex items-center gap-2">
        <StatusDot state={connectedMetadata === metadata.length ? "connected" : connectedMetadata > 0 ? "connecting" : "error"} />
        <span className="text-xs text-zinc-400">
          <span className="font-medium text-zinc-300">{connectedMetadata}/{metadata.length}</span> Metadata
        </span>
      </div>
    </div>
  );
}

// ============================================================================
// SERVICE ROW - Individual service in detailed view
// ============================================================================

function ServiceRow({ service }: { service: ServiceStatus }) {
  return (
    <div className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-zinc-800/30 transition-colors">
      <div className="flex items-center gap-3">
        <StatusDot state={service.state} size="md" />
        <div>
          <p className="text-sm font-medium text-zinc-200">{service.displayName}</p>
          {service.error && (
            <p className="text-xs text-red-400">{service.error}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        {service.latency !== undefined && (
          <span className="text-xs font-mono text-zinc-500">{service.latency}ms</span>
        )}
        <Badge
          variant={service.state === "connected" ? "success" : service.state === "connecting" ? "warning" : "error"}
          size="sm"
        >
          {service.state === "connected" ? "Online" : service.state === "connecting" ? "Connecting" : "Offline"}
        </Badge>
      </div>
    </div>
  );
}

// ============================================================================
// DETAILED CONNECTION STATUS - For settings page
// ============================================================================

export function ConnectionStatusDetailed({ className }: { className?: string }) {
  const { services, isLoading, refetch } = useServiceStatus();

  const sources = services.filter(s =>
    PLATFORMS.some(p => p.name === s.name && p.category === "source")
  );
  const targets = services.filter(s =>
    PLATFORMS.some(p => p.name === s.name && p.category === "target")
  );
  const metadata = services.filter(s =>
    METADATA_SOURCES.some(m => m.name === s.name)
  );

  const totalConnected = services.filter(s => s.state === "connected").length;
  const overallState: ConnectionState =
    totalConnected === services.length ? "connected" :
    totalConnected > services.length / 2 ? "connecting" :
    totalConnected > 0 ? "error" : "disconnected";

  return (
    <Card variant="bordered" className={clsx("animate-slide-up", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-needle/20 to-accent-safe/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
              </svg>
            </div>
            <div>
              <CardTitle>Service Connections</CardTitle>
              <CardDescription>Status of all connected platforms and services</CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge
              variant={overallState === "connected" ? "success" : overallState === "connecting" ? "warning" : "error"}
              size="sm"
              pulse={overallState === "connecting"}
            >
              {totalConnected}/{services.length} Online
            </Badge>
            <button
              onClick={refetch}
              disabled={isLoading}
              className="p-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-700/50 text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              title="Refresh status"
            >
              <svg className={clsx("w-4 h-4", isLoading && "animate-spin")} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 gap-3">
            <Spinner size="md" />
            <span className="text-zinc-400">Checking service connections...</span>
          </div>
        ) : (
          <>
            {/* Source Platforms */}
            <div>
              <h4 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
                </svg>
                Source Platforms
              </h4>
              <div className="bg-zinc-900/50 rounded-xl border border-zinc-800/50 divide-y divide-zinc-800/50">
                {sources.map((service) => (
                  <ServiceRow key={service.name} service={service} />
                ))}
              </div>
            </div>

            {/* Target Platforms */}
            <div>
              <h4 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Targets
              </h4>
              <div className="bg-zinc-900/50 rounded-xl border border-zinc-800/50 divide-y divide-zinc-800/50">
                {targets.map((service) => (
                  <ServiceRow key={service.name} service={service} />
                ))}
              </div>
            </div>

            {/* Metadata Sources */}
            <div>
              <h4 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                </svg>
                Metadata & Lyrics
              </h4>
              <div className="bg-zinc-900/50 rounded-xl border border-zinc-800/50 divide-y divide-zinc-800/50">
                {metadata.map((service) => (
                  <ServiceRow key={service.name} service={service} />
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default {
  ConnectionStatusCompact,
  ConnectionStatusDetailed,
};
