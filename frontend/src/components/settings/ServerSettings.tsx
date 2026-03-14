import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  Input,
  Select,
  ToggleSwitch,
} from "@/components/ui";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

const TIMEOUT_OPTIONS = [
  { value: "10", label: "10 seconds" },
  { value: "30", label: "30 seconds" },
  { value: "60", label: "1 minute" },
  { value: "120", label: "2 minutes" },
  { value: "300", label: "5 minutes" },
];

export function ServerSettings() {
  const {
    apiUrl,
    apiTimeout,
    offlineMode,
    update,
  } = useSettingsStore();

  const { changeInput, showSuccess, triggerAutoSave, changeSetting } = useSettingsContext();

  return (
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
          onChange={changeInput("apiUrl", "API URL")}
          placeholder="http://localhost:8000"
        />

        <Select
          label="API Timeout"
          options={TIMEOUT_OPTIONS}
          value={String(apiTimeout)}
          onChange={(e) => {
            update("apiTimeout", Number(e.target.value));
            showSuccess("API Timeout updated");
            triggerAutoSave();
          }}
        />

        <ToggleSwitch
          checked={offlineMode}
          onChange={(val) => changeSetting("offlineMode", val, "Offline mode")}
          label="Offline mode"
          description="Use local matching when server is unavailable"
        />
      </CardContent>
    </Card>
  );
}
