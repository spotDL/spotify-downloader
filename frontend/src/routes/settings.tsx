import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from "react";
import { useSettingsStore } from "@/stores/settings";
import {
  useUpdateUserSettings,
  storeToApiSettings,
} from "@/api";
import { useAuthStore } from "@/stores/auth";
import {
  Badge,
  EqualizerLoader,
  ConnectionStatusDetailed,
  useToast,
} from "@/components/ui";
import { useDevConfig } from "@/contexts/DevConfigContext";
import { config } from "@/config";
import { useDebounce } from "@/hooks/useDebounce";
import {
  SettingsProvider,
  DownloadSettings,
  MetadataSettings,
  DownloadFeaturesSettings,
  ProviderSettings,
  MatchingSettings,
  CredentialSettings,
  ServerSettings,
  AppearanceSettings,
  AdvancedSettings,
  SyncSettings,
} from "@/components/settings";

export const Route = createFileRoute("/settings")({
  beforeLoad: () => {
    if (config.mode === "hosted") {
      throw redirect({
        to: "/",
      });
    }

    const { isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated) {
      throw redirect({
        to: "/auth/login",
        search: {
          redirect: "/settings",
        },
      });
    }
  },
  component: SettingsPage,
});

function SettingsPage() {
  const { isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();
  const { error: showError } = useToast();
  const [autoSaveStatus, setAutoSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");

  const exportSettings = useSettingsStore((s) => s.exportSettings);

  // Track settings version for auto-save
  const settingsVersion = useRef(0);
  const [pendingSave, setPendingSave] = useState(0);
  const debouncedPendingSave = useDebounce(pendingSave, 2000);

  const triggerPendingSave = useCallback(() => {
    setPendingSave(prev => prev + 1);
  }, []);

  // API hooks for syncing
  const updateSettingsMutation = useUpdateUserSettings();

  // Auto-save to server when settings change (debounced)
  useEffect(() => {
    if (!isAuthenticated || debouncedPendingSave === 0) return;
    if (settingsVersion.current === debouncedPendingSave) return;
    settingsVersion.current = debouncedPendingSave;

    const autoSave = async () => {
      setAutoSaveStatus("saving");
      try {
        const currentSettings = exportSettings();
        await updateSettingsMutation.mutateAsync(
          storeToApiSettings(currentSettings)
        );
        setAutoSaveStatus("saved");
        setTimeout(() => setAutoSaveStatus("idle"), 2000);
      } catch (error) {
        setAutoSaveStatus("error");
        const message = error instanceof Error ? error.message : "Unknown error";
        showError(`Failed to auto-save settings: ${message}`);
        setTimeout(() => setAutoSaveStatus("idle"), 3000);
      }
    };

    autoSave();
  }, [debouncedPendingSave, isAuthenticated, exportSettings, updateSettingsMutation, showError]);

  return (
    <SettingsProvider onPendingSave={triggerPendingSave}>
      <div className="space-y-8 max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
              Settings
            </h1>
            <p className="text-[var(--color-text-muted)] mt-2">
              {features.hasDownloadSettings
                ? "Configure download preferences, credentials, and server connection"
                : "Configure server connection and preferences"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {isAuthenticated && autoSaveStatus === "saving" && (
              <Badge variant="info">
                <svg className="w-3 h-3 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Saving...
              </Badge>
            )}
            {isAuthenticated && autoSaveStatus === "saved" && (
              <Badge variant="success">
                <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Saved
              </Badge>
            )}
            {isAuthenticated && autoSaveStatus === "error" && (
              <Badge variant="error">
                Save failed
              </Badge>
            )}
            {isAuthenticated && (
              <Badge variant="success" pulse>
                Signed In
              </Badge>
            )}
            <EqualizerLoader />
          </div>
        </div>

        {/* Download Settings - Only shown in self-hosted mode */}
        {features.hasDownloadSettings && (
          <>
            <DownloadSettings />
            <MetadataSettings />
            <DownloadFeaturesSettings />
            <ProviderSettings />
          </>
        )}

        {/* Connection Status - Detailed */}
        <ConnectionStatusDetailed className="stagger-2" />

        <MatchingSettings />
        <CredentialSettings />
        <ServerSettings />
        <AppearanceSettings />
        <AdvancedSettings />
        <SyncSettings />
      </div>
    </SettingsProvider>
  );
}
