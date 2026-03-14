import { useState } from "react";
import { useSettingsStore } from "@/stores/settings";
import {
  useUserSettings,
  useUpdateUserSettings,
  apiToStoreSettings,
  storeToApiSettings,
} from "@/api";
import { useAuthStore } from "@/stores/auth";
import {
  Card,
  CardContent,
  CardHeader,
  Button,
  Badge,
  useToast,
} from "@/components/ui";
import { SectionHeader } from "./SectionHeader";

export function SyncSettings() {
  const { isAuthenticated } = useAuthStore();
  const { success: showSuccess, error: showError } = useToast();
  const [syncStatus, setSyncStatus] = useState<
    "idle" | "syncing" | "success" | "error"
  >("idle");

  const {
    exportSettings,
    importSettings,
    resetToDefaults,
  } = useSettingsStore();

  const { refetch: refetchServerSettings } = useUserSettings();
  const updateSettingsMutation = useUpdateUserSettings();

  // Sync settings to server
  const handleSyncToServer = async () => {
    if (!isAuthenticated) return;
    setSyncStatus("syncing");
    try {
      const currentSettings = exportSettings();
      await updateSettingsMutation.mutateAsync(
        storeToApiSettings(currentSettings)
      );
      setSyncStatus("success");
      showSuccess("Settings saved to server");
      setTimeout(() => setSyncStatus("idle"), 2000);
    } catch {
      setSyncStatus("error");
      showError("Failed to save settings to server");
      setTimeout(() => setSyncStatus("idle"), 3000);
    }
  };

  // Load settings from server
  const handleLoadFromServer = async () => {
    if (!isAuthenticated) return;
    setSyncStatus("syncing");
    try {
      const result = await refetchServerSettings();
      if (result.data) {
        importSettings(apiToStoreSettings(result.data));
      }
      setSyncStatus("success");
      showSuccess("Settings loaded from server");
      setTimeout(() => setSyncStatus("idle"), 2000);
    } catch {
      setSyncStatus("error");
      showError("Failed to load settings from server");
      setTimeout(() => setSyncStatus("idle"), 3000);
    }
  };

  // Export settings as JSON file
  const handleExportToFile = () => {
    const settings = exportSettings();
    const blob = new Blob([JSON.stringify(settings, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "spotdl-settings.json";
    a.click();
    URL.revokeObjectURL(url);
    showSuccess("Settings exported to file");
  };

  // Reset settings to defaults
  const handleResetToDefaults = () => {
    resetToDefaults();
    showSuccess("Settings reset to defaults");
  };

  // Import settings from JSON file
  const handleImportFromFile = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const settings = JSON.parse(text);
        importSettings(settings);
        showSuccess("Settings imported from file");
      } catch {
        showError("Failed to import settings. Please check the file format.");
      }
    };
    input.click();
  };

  return (
    <Card variant="bordered" className="animate-slide-up stagger-7">
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          }
          iconBg="bg-gradient-to-br from-fuchsia-500/20 to-pink-500/20"
          iconColor="text-fuchsia-400"
          title="Sync & Backup"
          description="Sync settings with server or export to file"
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Server Sync - Only for authenticated users */}
        {isAuthenticated ? (
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              onClick={handleSyncToServer}
              disabled={syncStatus === "syncing"}
            >
              {syncStatus === "syncing" ? (
                <>
                  <svg
                    className="w-4 h-4 mr-2 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Syncing...
                </>
              ) : (
                <>
                  <svg
                    className="w-4 h-4 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  Save to Server
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={handleLoadFromServer}
              disabled={syncStatus === "syncing"}
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                />
              </svg>
              Load from Server
            </Button>
            {syncStatus === "success" && (
              <Badge variant="success">Synced!</Badge>
            )}
            {syncStatus === "error" && (
              <Badge variant="error">Sync failed</Badge>
            )}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)]">
            Sign in to sync settings with the server
          </p>
        )}

        {/* File Import/Export */}
        <div className="flex flex-wrap gap-3 pt-2 border-t border-[var(--color-border-subtle)]">
          <Button variant="ghost" onClick={handleExportToFile}>
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Export to File
          </Button>
          <Button variant="ghost" onClick={handleImportFromFile}>
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Import from File
          </Button>
        </div>

        {/* Reset */}
        <div className="flex justify-end pt-2 border-t border-[var(--color-border-subtle)]">
          <Button variant="outline" onClick={handleResetToDefaults}>
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Reset to Defaults
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
