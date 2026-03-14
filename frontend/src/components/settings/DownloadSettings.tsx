import { useSettingsStore } from "@/stores/settings";
import type { AudioQuality, FilenameRestrict } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  Input,
  Select,
  Slider,
} from "@/components/ui";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

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

const OVERWRITE_OPTIONS = [
  { value: "skip", label: "Skip existing" },
  { value: "force", label: "Overwrite" },
  { value: "metadata", label: "Update metadata only" },
];

const RESTRICT_OPTIONS = [
  { value: "", label: "Default" },
  { value: "strict", label: "Strict (ASCII-safe)" },
  { value: "loose", label: "Loose (remove accents)" },
];

export function DownloadSettings() {
  const {
    audioFormat,
    audioQuality,
    outputTemplate,
    outputDirectory,
    maxConcurrentDownloads,
    overwrite,
    restrict,
    update,
  } = useSettingsStore();

  const { changeSelect, changeInput, showSuccess, triggerAutoSave } = useSettingsContext();

  return (
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
            onChange={changeSelect("audioFormat", "Audio format")}
          />
          <Select
            label="Audio Quality"
            options={QUALITY_OPTIONS}
            value={audioQuality}
            onChange={changeSelect("audioQuality", "Audio quality")}
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
            if (val >= 320) update("audioQuality", "best");
            else update("audioQuality", `${val}k` as AudioQuality);
            showSuccess("Bitrate updated");
            triggerAutoSave();
          }}
          formatValue={(v) => `${v} kbps`}
          disabled={audioFormat === "flac" || audioFormat === "wav"}
        />

        {/* Output Template */}
        <div>
          <Input
            label="Output Template"
            value={outputTemplate}
            onChange={changeInput("outputTemplate", "Output template")}
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
              {"{album-artist}"}
            </code>
            ,{" "}
            <code className="text-[var(--color-text-muted)]">
              {"{year}"}
            </code>
            ,{" "}
            <code className="text-[var(--color-text-muted)]">
              {"{track_number}"}
            </code>
            ,{" "}
            <code className="text-[var(--color-text-muted)]">
              {"{genre}"}
            </code>
            ,{" "}
            <code className="text-[var(--color-text-muted)]">
              {"{isrc}"}
            </code>
            ,{" "}
            <code className="text-[var(--color-text-muted)]">
              {"{list-name}"}
            </code>
            ,{" "}
            <code className="text-[var(--color-text-muted)]">
              {"{list-position}"}
            </code>
          </p>
        </div>

        {/* Output Location */}
        <Input
          label="Output Directory"
          value={outputDirectory}
          onChange={changeInput("outputDirectory", "Output directory")}
          placeholder="~/Music/SpotDL"
        />

        {/* Concurrent Downloads Slider */}
        <Slider
          label="Concurrent Downloads"
          value={maxConcurrentDownloads}
          min={1}
          max={10}
          step={1}
          onChange={(val) => {
            update("maxConcurrentDownloads", val);
            showSuccess("Concurrent downloads updated");
            triggerAutoSave();
          }}
          formatValue={(v) => `${v} download${v > 1 ? "s" : ""}`}
        />

        {/* Overwrite Mode */}
        <Select
          label="Existing Files"
          options={OVERWRITE_OPTIONS}
          value={overwrite}
          onChange={changeSelect("overwrite", "Existing files mode")}
        />

        {/* Filename Sanitization */}
        <Select
          label="Filename Sanitization"
          options={RESTRICT_OPTIONS}
          value={restrict ?? ""}
          onChange={(e) => {
            const val = e.target.value;
            update("restrict", val ? val as FilenameRestrict : null);
            showSuccess("Filename sanitization updated");
            triggerAutoSave();
          }}
        />
      </CardContent>
    </Card>
  );
}
