import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  SortableProviderList,
} from "@/components/ui";
import { useProviders } from "@/api";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

export function ProviderSettings() {
  const {
    metadataSourcePreferences,
    lyricsSourcePreferences,
    update,
    toggleProvider,
  } = useSettingsStore();

  const { data: providersData } = useProviders();
  const { showSuccess, triggerAutoSave } = useSettingsContext();

  return (
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
            onReorder={(prefs) => {
              update("metadataSourcePreferences", prefs);
              showSuccess("Metadata sources order updated");
              triggerAutoSave();
            }}
            onToggle={(id) => {
              toggleProvider("metadata", id);
              showSuccess("Metadata source toggled");
              triggerAutoSave();
            }}
          />
        )}

        {/* Lyrics Source Preferences */}
        {providersData && (
          <SortableProviderList
            label="Lyrics Sources"
            description="Order of preference for fetching lyrics"
            preferences={lyricsSourcePreferences}
            providers={providersData.lyrics_sources}
            onReorder={(prefs) => {
              update("lyricsSourcePreferences", prefs);
              showSuccess("Lyrics sources order updated");
              triggerAutoSave();
            }}
            onToggle={(id) => {
              toggleProvider("lyrics", id);
              showSuccess("Lyrics source toggled");
              triggerAutoSave();
            }}
          />
        )}
      </CardContent>
    </Card>
  );
}
