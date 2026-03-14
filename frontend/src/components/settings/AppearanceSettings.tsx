import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  ToggleSwitch,
} from "@/components/ui";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

export function AppearanceSettings() {
  const {
    compactSidebar,
    enableAnimations,
    reduceMotion,
  } = useSettingsStore();

  const { changeSetting } = useSettingsContext();

  return (
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
          onChange={(val) => changeSetting("compactSidebar", val, "Compact sidebar")}
          label="Compact sidebar"
          description="Use icon-only sidebar by default"
        />

        <ToggleSwitch
          checked={enableAnimations}
          onChange={(val) => changeSetting("enableAnimations", val, "Enable animations")}
          label="Enable animations"
          description="Show smooth transitions and VU meter effects"
        />

        <ToggleSwitch
          checked={reduceMotion}
          onChange={(val) => changeSetting("reduceMotion", val, "Reduce motion")}
          label="Reduce motion"
          description="Minimize animations for accessibility"
        />
      </CardContent>
    </Card>
  );
}
