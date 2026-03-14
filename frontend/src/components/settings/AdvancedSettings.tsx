import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  Input,
  Select,
  Slider,
} from "@/components/ui";
import { useDevConfig } from "@/contexts/DevConfigContext";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

const LOG_LEVEL_OPTIONS = [
  { value: "DEBUG", label: "Debug" },
  { value: "INFO", label: "Info" },
  { value: "WARNING", label: "Warning" },
  { value: "ERROR", label: "Error" },
  { value: "CRITICAL", label: "Critical" },
];

export function AdvancedSettings() {
  const {
    logLevel,
    cookieFile,
    proxy,
    ffmpegArgs,
    ytDlpArgs,
    maxFilenameLength,
    update,
  } = useSettingsStore();

  const { features } = useDevConfig();
  const { changeSelect, changeInput, showSuccess, triggerAutoSave } = useSettingsContext();

  return (
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
          description="Proxy, custom arguments, and other advanced options"
        />
      </CardHeader>
      <CardContent className="space-y-5">
        <Select
          label="Log Level"
          options={LOG_LEVEL_OPTIONS}
          value={logLevel}
          onChange={changeSelect("logLevel", "Log level")}
        />

        <Input
          label="Cookie File Path"
          value={cookieFile}
          onChange={changeInput("cookieFile", "Cookie file path")}
          placeholder="Path to cookies.txt for authentication"
        />

        <Input
          label="Proxy"
          value={proxy}
          onChange={changeInput("proxy", "Proxy")}
          placeholder="http://proxy:port or socks5://proxy:port"
        />

        <Input
          label="Custom FFmpeg Arguments"
          value={ffmpegArgs}
          onChange={changeInput("ffmpegArgs", "FFmpeg args")}
          placeholder="e.g. -ac 2 -ar 44100"
        />

        <Input
          label="Custom yt-dlp Arguments"
          value={ytDlpArgs}
          onChange={changeInput("ytDlpArgs", "yt-dlp args")}
          placeholder="e.g. --geo-bypass --extractor-retries 3"
        />

        {features.hasDownloadSettings && (
          <Slider
            label="Max Filename Length"
            value={maxFilenameLength}
            min={50}
            max={500}
            step={5}
            onChange={(val) => {
              update("maxFilenameLength", val);
              showSuccess("Max filename length updated");
              triggerAutoSave();
            }}
            formatValue={(v) => `${v} chars`}
          />
        )}
      </CardContent>
    </Card>
  );
}
