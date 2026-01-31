import { createFileRoute } from "@tanstack/react-router";
import {
  useSettingsStore,
  type AudioFormat,
  type AudioQuality,
} from "@/stores/settings";
import {
  Button,
  Input,
  Select,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui";
import { features } from "@/config";

export const Route = createFileRoute("/settings")({
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

const CONCURRENT_OPTIONS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16].map((n) => ({
  value: String(n),
  label: `${n} downloads`,
}));

// Custom checkbox component
function Checkbox({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <label className="flex items-start gap-4 cursor-pointer group p-3 -m-3 rounded-xl hover:bg-zinc-800/30 transition-colors">
      <div className="relative mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <div className="w-5 h-5 rounded-md border-2 border-zinc-600 bg-zinc-800 peer-checked:bg-emerald-500 peer-checked:border-emerald-500 transition-all">
          <svg
            className={`w-full h-full text-white p-0.5 transition-opacity ${checked ? "opacity-100" : "opacity-0"}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-zinc-200 font-medium">{label}</span>
        {description && (
          <p className="text-sm text-zinc-500 mt-0.5">{description}</p>
        )}
      </div>
    </label>
  );
}

function SettingsPage() {
  const {
    audioFormat,
    audioQuality,
    outputTemplate,
    maxConcurrentDownloads,
    overwriteExisting,
    embedMetadata,
    embedLyrics,
    embedCoverArt,
    apiUrl,
    offlineMode,
    setAudioFormat,
    setAudioQuality,
    setOutputTemplate,
    setMaxConcurrentDownloads,
    setOverwriteExisting,
    setEmbedMetadata,
    setEmbedLyrics,
    setEmbedCoverArt,
    setApiUrl,
    setOfflineMode,
    resetToDefaults,
  } = useSettingsStore();

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-zinc-50">Settings</h1>
        <p className="text-zinc-400 mt-2">
          {features.hasDownloadSettings
            ? "Configure download preferences and server connection"
            : "Configure server connection and preferences"}
        </p>
      </div>

      {/* Download Settings - Only shown in self-hosted mode */}
      {features.hasDownloadSettings && (
      <>
      <Card variant="bordered" className="animate-slide-up">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <div>
              <CardTitle>Download Options</CardTitle>
              <CardDescription>
                Configure audio format, quality, and output settings
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Audio Format"
              options={FORMAT_OPTIONS}
              value={audioFormat}
              onChange={(e) => setAudioFormat(e.target.value as AudioFormat)}
            />
            <Select
              label="Audio Quality"
              options={QUALITY_OPTIONS}
              value={audioQuality}
              onChange={(e) => setAudioQuality(e.target.value as AudioQuality)}
            />
          </div>

          <div>
            <Input
              label="Output Template"
              value={outputTemplate}
              onChange={(e) => setOutputTemplate(e.target.value)}
              placeholder="{artist} - {title}"
            />
            <p className="text-xs text-zinc-500 mt-2">
              Available: <code className="text-zinc-400">{"{artist}"}</code>, <code className="text-zinc-400">{"{artists}"}</code>, <code className="text-zinc-400">{"{title}"}</code>, <code className="text-zinc-400">{"{album}"}</code>, <code className="text-zinc-400">{"{year}"}</code>, <code className="text-zinc-400">{"{track_number}"}</code>
            </p>
          </div>

          <Select
            label="Concurrent Downloads"
            options={CONCURRENT_OPTIONS}
            value={String(maxConcurrentDownloads)}
            onChange={(e) => setMaxConcurrentDownloads(Number(e.target.value))}
          />

          <Checkbox
            checked={overwriteExisting}
            onChange={setOverwriteExisting}
            label="Overwrite existing files"
            description="Replace files that already exist in the output directory"
          />
        </CardContent>
      </Card>

      {/* Metadata Settings */}
      <Card variant="bordered" className="animate-slide-up stagger-1">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
              </svg>
            </div>
            <div>
              <CardTitle>Metadata Embedding</CardTitle>
              <CardDescription>
                Choose what metadata to embed in downloaded files
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <Checkbox
            checked={embedMetadata}
            onChange={setEmbedMetadata}
            label="Embed metadata"
            description="Title, artist, album, year, track number"
          />

          <Checkbox
            checked={embedLyrics}
            onChange={setEmbedLyrics}
            label="Embed lyrics"
            description="Fetch and embed synchronized lyrics when available"
          />

          <Checkbox
            checked={embedCoverArt}
            onChange={setEmbedCoverArt}
            label="Embed cover art"
            description="Download and embed album artwork"
          />
        </CardContent>
      </Card>
      </>
      )}

      {/* Server Settings */}
      <Card variant="bordered" className="animate-slide-up stagger-2">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-blue-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
            </div>
            <div>
              <CardTitle>Server Connection</CardTitle>
              <CardDescription>
                Configure backend API connection
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <Input
            label="API URL"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />

          <Checkbox
            checked={offlineMode}
            onChange={setOfflineMode}
            label="Offline mode"
            description="Use local matching when server is unavailable"
          />
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4">
        <Button variant="outline" onClick={resetToDefaults}>
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
