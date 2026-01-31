import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AudioFormat = "mp3" | "flac" | "ogg" | "m4a" | "opus" | "wav";
export type AudioQuality = "best" | "320k" | "256k" | "192k" | "128k";
export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export interface SettingsState {
  // Download settings
  audioFormat: AudioFormat;
  audioQuality: AudioQuality;
  outputTemplate: string;
  outputDirectory: string;
  maxConcurrentDownloads: number;
  overwriteExisting: boolean;

  // Metadata settings
  embedMetadata: boolean;
  embedLyrics: boolean;
  embedCoverArt: boolean;

  // Spotify credentials
  spotifyClientId: string;
  spotifyClientSecret: string;
  spotifyUserAuth: boolean;

  // Server settings
  apiUrl: string;
  apiTimeout: number;
  offlineMode: boolean;

  // Matching thresholds (for offline mode)
  nameMatchThreshold: number;
  artistMatchThreshold: number;
  timeMatchThreshold: number;

  // Advanced settings
  logLevel: LogLevel;
  cookieFile: string;

  // Sync status
  lastSyncedAt: string | null;
  isSyncing: boolean;

  // Actions
  setAudioFormat: (format: AudioFormat) => void;
  setAudioQuality: (quality: AudioQuality) => void;
  setOutputTemplate: (template: string) => void;
  setOutputDirectory: (directory: string) => void;
  setMaxConcurrentDownloads: (max: number) => void;
  setOverwriteExisting: (overwrite: boolean) => void;
  setEmbedMetadata: (embed: boolean) => void;
  setEmbedLyrics: (embed: boolean) => void;
  setEmbedCoverArt: (embed: boolean) => void;
  setSpotifyClientId: (id: string) => void;
  setSpotifyClientSecret: (secret: string) => void;
  setSpotifyUserAuth: (auth: boolean) => void;
  setApiUrl: (url: string) => void;
  setApiTimeout: (timeout: number) => void;
  setOfflineMode: (offline: boolean) => void;
  setNameMatchThreshold: (threshold: number) => void;
  setArtistMatchThreshold: (threshold: number) => void;
  setTimeMatchThreshold: (threshold: number) => void;
  setLogLevel: (level: LogLevel) => void;
  setCookieFile: (file: string) => void;
  resetToDefaults: () => void;
  setSyncing: (syncing: boolean) => void;
  setLastSyncedAt: (timestamp: string | null) => void;
  importSettings: (settings: Partial<SettingsState>) => void;
  exportSettings: () => ExportableSettings;
}

// Settings that can be exported/imported
export interface ExportableSettings {
  audioFormat: AudioFormat;
  audioQuality: AudioQuality;
  outputTemplate: string;
  outputDirectory: string;
  maxConcurrentDownloads: number;
  overwriteExisting: boolean;
  embedMetadata: boolean;
  embedLyrics: boolean;
  embedCoverArt: boolean;
  spotifyClientId: string;
  spotifyClientSecret: string;
  spotifyUserAuth: boolean;
  apiUrl: string;
  apiTimeout: number;
  offlineMode: boolean;
  nameMatchThreshold: number;
  artistMatchThreshold: number;
  timeMatchThreshold: number;
  logLevel: LogLevel;
  cookieFile: string;
}

const defaultSettings: ExportableSettings = {
  audioFormat: "mp3",
  audioQuality: "best",
  outputTemplate: "{artist} - {title}",
  outputDirectory: "",
  maxConcurrentDownloads: 3,
  overwriteExisting: false,
  embedMetadata: true,
  embedLyrics: true,
  embedCoverArt: true,
  spotifyClientId: "",
  spotifyClientSecret: "",
  spotifyUserAuth: false,
  apiUrl: "http://localhost:8000",
  apiTimeout: 30,
  offlineMode: false,
  nameMatchThreshold: 60,
  artistMatchThreshold: 70,
  timeMatchThreshold: 25,
  logLevel: "INFO",
  cookieFile: "",
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...defaultSettings,
      lastSyncedAt: null,
      isSyncing: false,

      setAudioFormat: (format) => set({ audioFormat: format }),
      setAudioQuality: (quality) => set({ audioQuality: quality }),
      setOutputTemplate: (template) => set({ outputTemplate: template }),
      setOutputDirectory: (directory) => set({ outputDirectory: directory }),
      setMaxConcurrentDownloads: (max) => set({ maxConcurrentDownloads: max }),
      setOverwriteExisting: (overwrite) => set({ overwriteExisting: overwrite }),
      setEmbedMetadata: (embed) => set({ embedMetadata: embed }),
      setEmbedLyrics: (embed) => set({ embedLyrics: embed }),
      setEmbedCoverArt: (embed) => set({ embedCoverArt: embed }),
      setSpotifyClientId: (id) => set({ spotifyClientId: id }),
      setSpotifyClientSecret: (secret) => set({ spotifyClientSecret: secret }),
      setSpotifyUserAuth: (auth) => set({ spotifyUserAuth: auth }),
      setApiUrl: (url) => set({ apiUrl: url }),
      setApiTimeout: (timeout) => set({ apiTimeout: timeout }),
      setOfflineMode: (offline) => set({ offlineMode: offline }),
      setNameMatchThreshold: (threshold) => set({ nameMatchThreshold: threshold }),
      setArtistMatchThreshold: (threshold) => set({ artistMatchThreshold: threshold }),
      setTimeMatchThreshold: (threshold) => set({ timeMatchThreshold: threshold }),
      setLogLevel: (level) => set({ logLevel: level }),
      setCookieFile: (file) => set({ cookieFile: file }),
      setSyncing: (syncing) => set({ isSyncing: syncing }),
      setLastSyncedAt: (timestamp) => set({ lastSyncedAt: timestamp }),

      resetToDefaults: () => set({ ...defaultSettings, lastSyncedAt: null }),

      importSettings: (settings) => {
        const current = get();
        set({
          audioFormat: settings.audioFormat ?? current.audioFormat,
          audioQuality: settings.audioQuality ?? current.audioQuality,
          outputTemplate: settings.outputTemplate ?? current.outputTemplate,
          outputDirectory: settings.outputDirectory ?? current.outputDirectory,
          maxConcurrentDownloads: settings.maxConcurrentDownloads ?? current.maxConcurrentDownloads,
          overwriteExisting: settings.overwriteExisting ?? current.overwriteExisting,
          embedMetadata: settings.embedMetadata ?? current.embedMetadata,
          embedLyrics: settings.embedLyrics ?? current.embedLyrics,
          embedCoverArt: settings.embedCoverArt ?? current.embedCoverArt,
          spotifyClientId: settings.spotifyClientId ?? current.spotifyClientId,
          spotifyClientSecret: settings.spotifyClientSecret ?? current.spotifyClientSecret,
          spotifyUserAuth: settings.spotifyUserAuth ?? current.spotifyUserAuth,
          apiUrl: settings.apiUrl ?? current.apiUrl,
          apiTimeout: settings.apiTimeout ?? current.apiTimeout,
          offlineMode: settings.offlineMode ?? current.offlineMode,
          nameMatchThreshold: settings.nameMatchThreshold ?? current.nameMatchThreshold,
          artistMatchThreshold: settings.artistMatchThreshold ?? current.artistMatchThreshold,
          timeMatchThreshold: settings.timeMatchThreshold ?? current.timeMatchThreshold,
          logLevel: settings.logLevel ?? current.logLevel,
          cookieFile: settings.cookieFile ?? current.cookieFile,
        });
      },

      exportSettings: () => {
        const state = get();
        return {
          audioFormat: state.audioFormat,
          audioQuality: state.audioQuality,
          outputTemplate: state.outputTemplate,
          outputDirectory: state.outputDirectory,
          maxConcurrentDownloads: state.maxConcurrentDownloads,
          overwriteExisting: state.overwriteExisting,
          embedMetadata: state.embedMetadata,
          embedLyrics: state.embedLyrics,
          embedCoverArt: state.embedCoverArt,
          spotifyClientId: state.spotifyClientId,
          spotifyClientSecret: state.spotifyClientSecret,
          spotifyUserAuth: state.spotifyUserAuth,
          apiUrl: state.apiUrl,
          apiTimeout: state.apiTimeout,
          offlineMode: state.offlineMode,
          nameMatchThreshold: state.nameMatchThreshold,
          artistMatchThreshold: state.artistMatchThreshold,
          timeMatchThreshold: state.timeMatchThreshold,
          logLevel: state.logLevel,
          cookieFile: state.cookieFile,
        };
      },
    }),
    {
      name: "spotdl-settings",
    }
  )
);
