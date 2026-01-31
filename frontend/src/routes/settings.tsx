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
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Settings</h1>
        <p className="text-gray-400 mt-1">
          Configure download preferences and server connection
        </p>
      </div>

      {/* Download Settings */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle>Download Options</CardTitle>
          <CardDescription>
            Configure audio format, quality, and output settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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

          <Input
            label="Output Template"
            value={outputTemplate}
            onChange={(e) => setOutputTemplate(e.target.value)}
            placeholder="{artist} - {title}"
          />
          <p className="text-xs text-gray-500 -mt-2">
            Available: {"{artist}"}, {"{artists}"}, {"{title}"}, {"{album}"},{" "}
            {"{year}"}, {"{track_number}"}
          </p>

          <Select
            label="Concurrent Downloads"
            options={CONCURRENT_OPTIONS}
            value={String(maxConcurrentDownloads)}
            onChange={(e) => setMaxConcurrentDownloads(Number(e.target.value))}
          />

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={overwriteExisting}
              onChange={(e) => setOverwriteExisting(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
            />
            <span className="text-gray-300">Overwrite existing files</span>
          </label>
        </CardContent>
      </Card>

      {/* Metadata Settings */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle>Metadata Embedding</CardTitle>
          <CardDescription>
            Choose what metadata to embed in downloaded files
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={embedMetadata}
              onChange={(e) => setEmbedMetadata(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
            />
            <div>
              <span className="text-gray-300">Embed metadata</span>
              <p className="text-xs text-gray-500">
                Title, artist, album, year, track number
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={embedLyrics}
              onChange={(e) => setEmbedLyrics(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
            />
            <div>
              <span className="text-gray-300">Embed lyrics</span>
              <p className="text-xs text-gray-500">
                Fetch and embed synchronized lyrics when available
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={embedCoverArt}
              onChange={(e) => setEmbedCoverArt(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
            />
            <div>
              <span className="text-gray-300">Embed cover art</span>
              <p className="text-xs text-gray-500">
                Download and embed album artwork
              </p>
            </div>
          </label>
        </CardContent>
      </Card>

      {/* Server Settings */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle>Server Connection</CardTitle>
          <CardDescription>
            Configure backend API connection
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="API URL"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={offlineMode}
              onChange={(e) => setOfflineMode(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
            />
            <div>
              <span className="text-gray-300">Offline mode</span>
              <p className="text-xs text-gray-500">
                Use local matching when server is unavailable
              </p>
            </div>
          </label>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={resetToDefaults}>
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
