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

export function DownloadFeaturesSettings() {
  const {
    sponsorBlock,
    skipExplicit,
    scanForSongs,
    playlistNumbering,
    fetchAlbums,
    m3u,
    archive,
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
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          }
          iconBg="bg-gradient-to-br from-amber-500/20 to-orange-500/20"
          iconColor="text-amber-400"
          title="Download Features"
          description="SponsorBlock, playlists, content filtering, and more"
        />
      </CardHeader>
      <CardContent className="space-y-4">
        <ToggleSwitch
          checked={sponsorBlock}
          onChange={(val) => changeSetting("sponsorBlock", val, "SponsorBlock")}
          label="SponsorBlock"
          description="Remove sponsor segments from YouTube audio"
        />

        <ToggleSwitch
          checked={skipExplicit}
          onChange={(val) => changeSetting("skipExplicit", val, "Skip explicit tracks")}
          label="Skip explicit tracks"
          description="Filter out explicit content from downloads"
        />

        <ToggleSwitch
          checked={scanForSongs}
          onChange={(val) => changeSetting("scanForSongs", val, "Scan for existing songs")}
          label="Scan for existing songs"
          description="Check local files by metadata to avoid duplicates"
        />

        <ToggleSwitch
          checked={playlistNumbering}
          onChange={(val) => changeSetting("playlistNumbering", val, "Playlist numbering")}
          label="Playlist numbering"
          description="Prepend track numbers to filenames in playlists"
        />

        <ToggleSwitch
          checked={fetchAlbums}
          onChange={(val) => changeSetting("fetchAlbums", val, "Fetch full albums")}
          label="Fetch full albums for artists"
          description="Download all album tracks when downloading an artist"
        />

        <Input
          label="M3U Playlist File"
          value={m3u}
          onChange={changeInput("m3u", "M3U template")}
          placeholder="e.g. {list}.m3u8"
        />

        <Input
          label="Archive File"
          value={archive}
          onChange={changeInput("archive", "Archive file")}
          placeholder="Path to archive file for tracking downloads"
        />
      </CardContent>
    </Card>
  );
}
