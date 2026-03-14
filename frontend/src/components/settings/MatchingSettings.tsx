import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  Slider,
  SortableProviderList,
  ToggleSwitch,
} from "@/components/ui";
import { useProviders } from "@/api";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

export function MatchingSettings() {
  const {
    audioSourcePreferences,
    nameMatchThreshold,
    artistMatchThreshold,
    timeMatchThreshold,
    offlineMode,
    update,
    toggleProvider,
  } = useSettingsStore();

  const { data: providersData } = useProviders();
  const { showSuccess, triggerAutoSave } = useSettingsContext();

  return (
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
            onReorder={(prefs) => {
              update("audioSourcePreferences", prefs);
              showSuccess("Audio sources order updated");
              triggerAutoSave();
            }}
            onToggle={(id) => {
              toggleProvider("audio", id);
              showSuccess("Audio source toggled");
              triggerAutoSave();
            }}
          />
        )}

        {/* Minimum Score Slider */}
        <Slider
          label="Minimum Match Score"
          value={nameMatchThreshold}
          min={0}
          max={100}
          step={5}
          onChange={(val) => {
            update("nameMatchThreshold", val);
            showSuccess("Minimum match score updated");
            triggerAutoSave();
          }}
          formatValue={(v) => `${v}%`}
        />

        {/* Auto-select Toggle */}
        <ToggleSwitch
          checked={!offlineMode}
          onChange={(checked) => {
            update("offlineMode", !checked);
            showSuccess("Auto-select best match updated");
            triggerAutoSave();
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
              onChange={(val) => {
                update("artistMatchThreshold", val);
                showSuccess("Artist match threshold updated");
                triggerAutoSave();
              }}
              formatValue={(v) => `${v}%`}
            />
            <Slider
              label="Duration Match Threshold"
              value={timeMatchThreshold}
              min={0}
              max={100}
              step={5}
              onChange={(val) => {
                update("timeMatchThreshold", val);
                showSuccess("Duration match threshold updated");
                triggerAutoSave();
              }}
              formatValue={(v) => `${v}%`}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
