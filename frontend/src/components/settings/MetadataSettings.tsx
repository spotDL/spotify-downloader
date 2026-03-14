import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  Input,
  ToggleSwitch,
} from "@/components/ui";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

export function MetadataSettings() {
  const {
    embedMetadata,
    embedLyrics,
    embedCover,
    generateLrc,
    id3Separator,
  } = useSettingsStore();

  const { changeSetting, changeInput } = useSettingsContext();

  return (
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
          title="Metadata & Lyrics"
          description="Choose what metadata to embed in downloaded files"
        />
      </CardHeader>
      <CardContent className="space-y-4">
        <ToggleSwitch
          checked={embedMetadata}
          onChange={(val) => changeSetting("embedMetadata", val, "Embed metadata")}
          label="Embed metadata"
          description="Title, artist, album, year, track number"
        />

        <ToggleSwitch
          checked={embedLyrics}
          onChange={(val) => changeSetting("embedLyrics", val, "Embed lyrics")}
          label="Embed lyrics"
          description="Fetch and embed synchronized lyrics when available"
        />

        <ToggleSwitch
          checked={embedCover}
          onChange={(val) => changeSetting("embedCover", val, "Embed cover art")}
          label="Embed cover art"
          description="Download and embed album artwork"
        />

        <ToggleSwitch
          checked={generateLrc}
          onChange={(val) => changeSetting("generateLrc", val, "Generate LRC files")}
          label="Generate LRC files"
          description="Create .lrc sidecar files with synced lyrics"
        />

        <Input
          label="ID3 Artist Separator"
          value={id3Separator}
          onChange={changeInput("id3Separator", "ID3 separator")}
          placeholder="/"
        />
      </CardContent>
    </Card>
  );
}
