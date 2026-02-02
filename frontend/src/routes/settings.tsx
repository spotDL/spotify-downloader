import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState } from "react";
import {
  useSettingsStore,
  type AudioFormat,
  type AudioQuality,
  type LogLevel,
} from "@/stores/settings";
import {
  useUserSettings,
  useUpdateUserSettings,
  apiToStoreSettings,
  storeToApiSettings,
} from "@/api";
import { useAuthStore } from "@/stores/auth";
import {
  Button,
  Input,
  Select,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Badge,
  ToggleSwitch,
  Slider,
  EqualizerLoader,
  ConnectionStatusDetailed,
  SortableProviderList,
  useToast,
} from "@/components/ui";
import { useProviders } from "@/api";
import { useDevConfig } from "@/contexts/DevConfigContext";

export const Route = createFileRoute("/settings")({
  beforeLoad: () => {
    const { isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated) {
      throw redirect({
        to: "/auth/login",
        search: {
          redirect: "/settings",
        },
      });
    }
  },
  component: SettingsPage,
});

const FORMAT_OPTIONS = [
  { value: "mp3", label: "MP3" },
  { value: "flac", label: "FLAC" },
  { value: "ogg", label: "OGG Vorbis" },
  { value: "m4a", label: "M4A (AAC)" },
  { value: "opus", label: "Opus" },
  { value: "wav", label: "WAV" },
];

const QUALITY_OPTIONS = [
  { value: "best", label: "Best Available" },
  { value: "320k", label: "320 kbps" },
  { value: "256k", label: "256 kbps" },
  { value: "192k", label: "192 kbps" },
  { value: "128k", label: "128 kbps" },
];

const LOG_LEVEL_OPTIONS = [
  { value: "DEBUG", label: "Debug" },
  { value: "INFO", label: "Info" },
  { value: "WARNING", label: "Warning" },
  { value: "ERROR", label: "Error" },
  { value: "CRITICAL", label: "Critical" },
];

const TIMEOUT_OPTIONS = [
  { value: "10", label: "10 seconds" },
  { value: "30", label: "30 seconds" },
  { value: "60", label: "1 minute" },
  { value: "120", label: "2 minutes" },
  { value: "300", label: "5 minutes" },
];

// Section header component
function SectionHeader({
  icon,
  iconBg,
  iconColor,
  title,
  description,
}: {
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`w-10 h-10 rounded-xl ${iconBg} flex items-center justify-center`}
      >
        <span className={iconColor}>{icon}</span>
      </div>
      <div>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </div>
    </div>
  );
}

function SettingsPage() {
  const { isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();
  const { success: showSuccess, error: showError } = useToast();
  const [showSecrets, setShowSecrets] = useState(false);
  const [syncStatus, setSyncStatus] = useState<
    "idle" | "syncing" | "success" | "error"
  >("idle");

  const {
    audioFormat,
    audioQuality,
    outputTemplate,
    outputDirectory,
    maxConcurrentDownloads,
    overwriteExisting,
    embedMetadata,
    embedLyrics,
    embedCoverArt,
    spotifyClientId,
    spotifyClientSecret,
    spotifyUserAuth,
    apiUrl,
    apiTimeout,
    offlineMode,
    nameMatchThreshold,
    artistMatchThreshold,
    timeMatchThreshold,
    logLevel,
    cookieFile,
    compactSidebar,
    enableAnimations,
    reduceMotion,
    audioSourcePreferences,
    metadataSourcePreferences,
    lyricsSourcePreferences,
    setAudioFormat,
    setAudioQuality,
    setOutputTemplate,
    setOutputDirectory,
    setMaxConcurrentDownloads,
    setOverwriteExisting,
    setEmbedMetadata,
    setEmbedLyrics,
    setEmbedCoverArt,
    setSpotifyClientId,
    setSpotifyClientSecret,
    setSpotifyUserAuth,
    setApiUrl,
    setApiTimeout,
    setOfflineMode,
    setNameMatchThreshold,
    setArtistMatchThreshold,
    setTimeMatchThreshold,
    setLogLevel,
    setCookieFile,
    setCompactSidebar,
    setEnableAnimations,
    setReduceMotion,
    setAudioSourcePreferences,
    setMetadataSourcePreferences,
    setLyricsSourcePreferences,
    toggleProvider,
    resetToDefaults,
    importSettings,
    exportSettings,
  } = useSettingsStore();

  // Fetch provider info from API
  const { data: providersData } = useProviders();

  // Wrapper functions that show toast on setting change
  const withToast = <T,>(setter: (value: T) => void, label: string) => (value: T) => {
    setter(value);
    showSuccess(`${label} updated`);
  };

  // API hooks for syncing
  const { refetch: refetchServerSettings } = useUserSettings();
  const updateSettingsMutation = useUpdateUserSettings();

  // Sync settings to server
  const handleSyncToServer = async () => {
    if (!isAuthenticated) return;
    setSyncStatus("syncing");
    try {
      const currentSettings = exportSettings();
      await updateSettingsMutation.mutateAsync(
        storeToApiSettings(currentSettings)
      );
      setSyncStatus("success");
      showSuccess("Settings saved to server");
      setTimeout(() => setSyncStatus("idle"), 2000);
    } catch {
      setSyncStatus("error");
      showError("Failed to save settings to server");
      setTimeout(() => setSyncStatus("idle"), 3000);
    }
  };

  // Load settings from server
  const handleLoadFromServer = async () => {
    if (!isAuthenticated) return;
    setSyncStatus("syncing");
    try {
      const result = await refetchServerSettings();
      if (result.data) {
        importSettings(apiToStoreSettings(result.data));
      }
      setSyncStatus("success");
      showSuccess("Settings loaded from server");
      setTimeout(() => setSyncStatus("idle"), 2000);
    } catch {
      setSyncStatus("error");
      showError("Failed to load settings from server");
      setTimeout(() => setSyncStatus("idle"), 3000);
    }
  };

  // Export settings as JSON file
  const handleExportToFile = () => {
    const settings = exportSettings();
    const blob = new Blob([JSON.stringify(settings, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "spotdl-settings.json";
    a.click();
    URL.revokeObjectURL(url);
    showSuccess("Settings exported to file");
  };

  // Reset settings to defaults
  const handleResetToDefaults = () => {
    resetToDefaults();
    showSuccess("Settings reset to defaults");
  };

  // Import settings from JSON file
  const handleImportFromFile = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const settings = JSON.parse(text);
        importSettings(settings);
        showSuccess("Settings imported from file");
      } catch {
        showError("Failed to import settings. Please check the file format.");
      }
    };
    input.click();
  };

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            Settings
          </h1>
          <p className="text-[var(--color-text-muted)] mt-2">
            {features.hasDownloadSettings
              ? "Configure download preferences, credentials, and server connection"
              : "Configure server connection and preferences"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isAuthenticated && (
            <Badge variant="success" pulse>
              Signed In
            </Badge>
          )}
          <EqualizerLoader />
        </div>
      </div>

      {/* Download Settings - Only shown in self-hosted mode */}
      {features.hasDownloadSettings && (
        <>
          {/* Download Preferences Section */}
          <Card variant="bordered" className="animate-slide-up">
            <CardHeader>
              <SectionHeader
                icon={
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
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                }
                iconBg="bg-gradient-to-br from-[var(--accent-safe)]/20 to-[var(--accent-cool)]/20"
                iconColor="text-[var(--accent-safe)]"
                title="Download Preferences"
                description="Configure audio format, quality, and output settings"
              />
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Format & Quality Row */}
              <div className="grid grid-cols-2 gap-4">
                <Select
                  label="Audio Format"
                  options={FORMAT_OPTIONS}
                  value={audioFormat}
                  onChange={(e) =>
                    setAudioFormat(e.target.value as AudioFormat)
                  }
                />
                <Select
                  label="Audio Quality"
                  options={QUALITY_OPTIONS}
                  value={audioQuality}
                  onChange={(e) =>
                    setAudioQuality(e.target.value as AudioQuality)
                  }
                />
              </div>

              {/* Bitrate Slider - shows current quality visualization */}
              <Slider
                label="Bitrate"
                value={
                  audioQuality === "best"
                    ? 320
                    : parseInt(audioQuality.replace("k", ""))
                }
                min={128}
                max={320}
                step={32}
                onChange={(val) => {
                  if (val >= 320) setAudioQuality("best");
                  else setAudioQuality(`${val}k` as AudioQuality);
                }}
                formatValue={(v) => `${v} kbps`}
                disabled={audioFormat === "flac" || audioFormat === "wav"}
              />

              {/* Output Template */}
              <div>
                <Input
                  label="Output Template"
                  value={outputTemplate}
                  onChange={(e) => setOutputTemplate(e.target.value)}
                  placeholder="{artist} - {title}"
                />
                <p className="text-xs text-[var(--color-text-dim)] mt-2">
                  Available:{" "}
                  <code className="text-[var(--color-text-muted)]">
                    {"{artist}"}
                  </code>
                  ,{" "}
                  <code className="text-[var(--color-text-muted)]">
                    {"{artists}"}
                  </code>
                  ,{" "}
                  <code className="text-[var(--color-text-muted)]">
                    {"{title}"}
                  </code>
                  ,{" "}
                  <code className="text-[var(--color-text-muted)]">
                    {"{album}"}
                  </code>
                  ,{" "}
                  <code className="text-[var(--color-text-muted)]">
                    {"{year}"}
                  </code>
                  ,{" "}
                  <code className="text-[var(--color-text-muted)]">
                    {"{track_number}"}
                  </code>
                </p>
              </div>

              {/* Output Location */}
              <Input
                label="Output Directory"
                value={outputDirectory}
                onChange={(e) => setOutputDirectory(e.target.value)}
                placeholder="~/Music/SpotDL"
              />

              {/* Concurrent Downloads Slider */}
              <Slider
                label="Concurrent Downloads"
                value={maxConcurrentDownloads}
                min={1}
                max={10}
                step={1}
                onChange={setMaxConcurrentDownloads}
                formatValue={(v) => `${v} download${v > 1 ? "s" : ""}`}
              />

              {/* Overwrite Toggle */}
              <ToggleSwitch
                checked={overwriteExisting}
                onChange={withToast(setOverwriteExisting, "Overwrite existing files")}
                label="Overwrite existing files"
                description="Replace files that already exist in the output directory"
              />
            </CardContent>
          </Card>

          {/* Metadata Embedding Section */}
          <Card variant="bordered" className="animate-slide-up stagger-1">
            <CardHeader>
              <SectionHeader
                icon={
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
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                }
                iconBg="bg-gradient-to-br from-violet-500/20 to-purple-500/20"
                iconColor="text-violet-400"
                title="Metadata Embedding"
                description="Choose what metadata to embed in downloaded files"
              />
            </CardHeader>
            <CardContent className="space-y-4">
              <ToggleSwitch
                checked={embedMetadata}
                onChange={withToast(setEmbedMetadata, "Embed metadata")}
                label="Embed metadata"
                description="Title, artist, album, year, track number"
              />

              <ToggleSwitch
                checked={embedLyrics}
                onChange={withToast(setEmbedLyrics, "Embed lyrics")}
                label="Embed lyrics"
                description="Fetch and embed synchronized lyrics when available"
              />

              <ToggleSwitch
                checked={embedCoverArt}
                onChange={withToast(setEmbedCoverArt, "Embed cover art")}
                label="Embed cover art"
                description="Download and embed album artwork"
              />
            </CardContent>
          </Card>

          {/* Source Preferences Section */}
          <Card variant="bordered" className="animate-slide-up stagger-2">
            <CardHeader>
              <SectionHeader
                icon={
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
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                    />
                  </svg>
                }
                iconBg="bg-gradient-to-br from-cyan-500/20 to-teal-500/20"
                iconColor="text-cyan-400"
                title="Source Preferences"
                description="Configure priority order for metadata and lyrics providers"
              />
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Metadata Source Preferences */}
              {providersData && (
                <SortableProviderList
                  label="Metadata Sources"
                  description="Order of preference for fetching song metadata"
                  preferences={metadataSourcePreferences}
                  providers={providersData.metadata_sources}
                  onReorder={setMetadataSourcePreferences}
                  onToggle={(id) => toggleProvider("metadata", id)}
                />
              )}

              {/* Lyrics Source Preferences */}
              {providersData && (
                <SortableProviderList
                  label="Lyrics Sources"
                  description="Order of preference for fetching lyrics"
                  preferences={lyricsSourcePreferences}
                  providers={providersData.lyrics_sources}
                  onReorder={setLyricsSourcePreferences}
                  onToggle={(id) => toggleProvider("lyrics", id)}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Connection Status - Detailed */}
      <ConnectionStatusDetailed className="stagger-2" />

      {/* Matching Preferences Section */}
      <Card variant="bordered" className="animate-slide-up stagger-3">
        <CardHeader>
          <SectionHeader
            icon={
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
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            }
            iconBg="bg-gradient-to-br from-[var(--accent-needle)]/20 to-[var(--accent-warm)]/20"
            iconColor="text-[var(--accent-needle)]"
            title="Matching Preferences"
            description="Configure how songs are matched to audio sources"
          />
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Audio Source Preferences */}
          {providersData && (
            <SortableProviderList
              label="Audio Sources"
              description="Drag to set priority order. Higher priority sources are tried first."
              preferences={audioSourcePreferences}
              providers={providersData.audio_sources}
              onReorder={setAudioSourcePreferences}
              onToggle={(id) => toggleProvider("audio", id)}
            />
          )}

          {/* Minimum Score Slider */}
          <Slider
            label="Minimum Match Score"
            value={nameMatchThreshold}
            min={0}
            max={100}
            step={5}
            onChange={setNameMatchThreshold}
            formatValue={(v) => `${v}%`}
          />

          {/* Auto-select Toggle */}
          <ToggleSwitch
            checked={!offlineMode}
            onChange={(checked) => {
              setOfflineMode(!checked);
              showSuccess("Auto-select best match updated");
            }}
            label="Auto-select best match"
            description="Automatically select the highest scoring match without manual review"
          />

          {/* Advanced Thresholds (collapsed by default) */}
          {offlineMode && (
            <div className="space-y-4 pt-4 border-t border-[var(--color-border-subtle)]">
              <p className="text-xs text-[var(--color-text-muted)]">
                Advanced Matching Thresholds
              </p>
              <Slider
                label="Artist Match Threshold"
                value={artistMatchThreshold}
                min={0}
                max={100}
                step={5}
                onChange={setArtistMatchThreshold}
                formatValue={(v) => `${v}%`}
              />
              <Slider
                label="Duration Match Threshold"
                value={timeMatchThreshold}
                min={0}
                max={100}
                step={5}
                onChange={setTimeMatchThreshold}
                formatValue={(v) => `${v}%`}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Spotify Credentials */}
      <Card variant="bordered" className="animate-slide-up stagger-3">
        <CardHeader>
          <SectionHeader
            icon={
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
              </svg>
            }
            iconBg="bg-gradient-to-br from-[#1db954]/20 to-[#169c46]/20"
            iconColor="text-[#1db954]"
            title="Spotify Credentials"
            description="Optional API credentials for better rate limits"
          />
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="p-3 rounded-lg bg-[var(--accent-warm)]/10 border border-[var(--accent-warm)]/20">
            <p className="text-sm text-[var(--accent-warm)]">
              Get your credentials from the{" "}
              <a
                href="https://developer.spotify.com/dashboard"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-[var(--accent-warm)]/80"
              >
                Spotify Developer Dashboard
              </a>
            </p>
          </div>

          <Input
            label="Client ID"
            value={spotifyClientId}
            onChange={(e) => setSpotifyClientId(e.target.value)}
            placeholder="Your Spotify Client ID"
          />

          <div className="relative">
            <Input
              label="Client Secret"
              type={showSecrets ? "text" : "password"}
              value={spotifyClientSecret}
              onChange={(e) => setSpotifyClientSecret(e.target.value)}
              placeholder="Your Spotify Client Secret"
            />
            <button
              type="button"
              onClick={() => setShowSecrets(!showSecrets)}
              className="absolute right-3 top-8 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              {showSecrets ? (
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
                    d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                  />
                </svg>
              ) : (
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
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
              )}
            </button>
          </div>

          <ToggleSwitch
            checked={spotifyUserAuth}
            onChange={withToast(setSpotifyUserAuth, "Spotify OAuth")}
            label="Use Spotify OAuth"
            description="Enable user authentication for accessing private playlists"
          />
        </CardContent>
      </Card>

      {/* Server Connection */}
      <Card variant="bordered" className="animate-slide-up stagger-4">
        <CardHeader>
          <SectionHeader
            icon={
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
                  d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
                />
              </svg>
            }
            iconBg="bg-gradient-to-br from-[var(--accent-cool)]/20 to-blue-500/20"
            iconColor="text-[var(--accent-cool)]"
            title="Server Connection"
            description="Configure backend API connection"
          />
        </CardHeader>
        <CardContent className="space-y-5">
          <Input
            label="API URL"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />

          <Select
            label="API Timeout"
            options={TIMEOUT_OPTIONS}
            value={String(apiTimeout)}
            onChange={(e) => setApiTimeout(Number(e.target.value))}
          />

          <ToggleSwitch
            checked={offlineMode}
            onChange={withToast(setOfflineMode, "Offline mode")}
            label="Offline mode"
            description="Use local matching when server is unavailable"
          />
        </CardContent>
      </Card>

      {/* Appearance Section */}
      <Card variant="bordered" className="animate-slide-up stagger-5">
        <CardHeader>
          <SectionHeader
            icon={
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
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                />
              </svg>
            }
            iconBg="bg-gradient-to-br from-pink-500/20 to-rose-500/20"
            iconColor="text-pink-400"
            title="Appearance"
            description="Customize the look and feel"
          />
        </CardHeader>
        <CardContent className="space-y-4">
          <ToggleSwitch
            checked={compactSidebar}
            onChange={withToast(setCompactSidebar, "Compact sidebar")}
            label="Compact sidebar"
            description="Use icon-only sidebar by default"
          />

          <ToggleSwitch
            checked={enableAnimations}
            onChange={withToast(setEnableAnimations, "Enable animations")}
            label="Enable animations"
            description="Show smooth transitions and VU meter effects"
          />

          <ToggleSwitch
            checked={reduceMotion}
            onChange={withToast(setReduceMotion, "Reduce motion")}
            label="Reduce motion"
            description="Minimize animations for accessibility"
          />
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card variant="bordered" className="animate-slide-up stagger-6">
        <CardHeader>
          <SectionHeader
            icon={
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
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            }
            iconBg="bg-gradient-to-br from-zinc-500/20 to-zinc-600/20"
            iconColor="text-zinc-400"
            title="Advanced"
            description="Additional configuration options"
          />
        </CardHeader>
        <CardContent className="space-y-5">
          <Select
            label="Log Level"
            options={LOG_LEVEL_OPTIONS}
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value as LogLevel)}
          />

          <Input
            label="Cookie File Path"
            value={cookieFile}
            onChange={(e) => setCookieFile(e.target.value)}
            placeholder="Path to cookies.txt for authentication"
          />
        </CardContent>
      </Card>

      {/* Sync & Actions */}
      <Card variant="bordered" className="animate-slide-up stagger-7">
        <CardHeader>
          <SectionHeader
            icon={
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
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            }
            iconBg="bg-gradient-to-br from-fuchsia-500/20 to-pink-500/20"
            iconColor="text-fuchsia-400"
            title="Sync & Backup"
            description="Sync settings with server or export to file"
          />
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Server Sync - Only for authenticated users */}
          {isAuthenticated ? (
            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={handleSyncToServer}
                disabled={syncStatus === "syncing"}
              >
                {syncStatus === "syncing" ? (
                  <>
                    <svg
                      className="w-4 h-4 mr-2 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Syncing...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    Save to Server
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={handleLoadFromServer}
                disabled={syncStatus === "syncing"}
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                  />
                </svg>
                Load from Server
              </Button>
              {syncStatus === "success" && (
                <Badge variant="success">Synced!</Badge>
              )}
              {syncStatus === "error" && (
                <Badge variant="error">Sync failed</Badge>
              )}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-muted)]">
              Sign in to sync settings with the server
            </p>
          )}

          {/* File Import/Export */}
          <div className="flex flex-wrap gap-3 pt-2 border-t border-[var(--color-border-subtle)]">
            <Button variant="ghost" onClick={handleExportToFile}>
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Export to File
            </Button>
            <Button variant="ghost" onClick={handleImportFromFile}>
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Import from File
            </Button>
          </div>

          {/* Reset */}
          <div className="flex justify-end pt-2 border-t border-[var(--color-border-subtle)]">
            <Button variant="outline" onClick={handleResetToDefaults}>
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Reset to Defaults
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
