import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AudioFormat = "mp3" | "flac" | "ogg" | "m4a" | "opus" | "wav";
export type AudioQuality = "best" | "320k" | "256k" | "192k" | "128k";

export interface SettingsState {
  // Download settings
  audioFormat: AudioFormat;
  audioQuality: AudioQuality;
  outputTemplate: string;
  maxConcurrentDownloads: number;
  overwriteExisting: boolean;

  // Metadata settings
  embedMetadata: boolean;
  embedLyrics: boolean;
  embedCoverArt: boolean;

  // Server settings
  apiUrl: string;
  offlineMode: boolean;

  // Actions
  setAudioFormat: (format: AudioFormat) => void;
  setAudioQuality: (quality: AudioQuality) => void;
  setOutputTemplate: (template: string) => void;
  setMaxConcurrentDownloads: (max: number) => void;
  setOverwriteExisting: (overwrite: boolean) => void;
  setEmbedMetadata: (embed: boolean) => void;
  setEmbedLyrics: (embed: boolean) => void;
  setEmbedCoverArt: (embed: boolean) => void;
  setApiUrl: (url: string) => void;
  setOfflineMode: (offline: boolean) => void;
  resetToDefaults: () => void;
}

const defaultSettings = {
  audioFormat: "mp3" as AudioFormat,
  audioQuality: "best" as AudioQuality,
  outputTemplate: "{artist} - {title}",
  maxConcurrentDownloads: 3,
  overwriteExisting: false,
  embedMetadata: true,
  embedLyrics: true,
  embedCoverArt: true,
  apiUrl: "http://localhost:8000",
  offlineMode: false,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultSettings,

      setAudioFormat: (format) => set({ audioFormat: format }),
      setAudioQuality: (quality) => set({ audioQuality: quality }),
      setOutputTemplate: (template) => set({ outputTemplate: template }),
      setMaxConcurrentDownloads: (max) => set({ maxConcurrentDownloads: max }),
      setOverwriteExisting: (overwrite) => set({ overwriteExisting: overwrite }),
      setEmbedMetadata: (embed) => set({ embedMetadata: embed }),
      setEmbedLyrics: (embed) => set({ embedLyrics: embed }),
      setEmbedCoverArt: (embed) => set({ embedCoverArt: embed }),
      setApiUrl: (url) => set({ apiUrl: url }),
      setOfflineMode: (offline) => set({ offlineMode: offline }),
      resetToDefaults: () => set(defaultSettings),
    }),
    {
      name: "spotdl-settings",
    }
  )
);
