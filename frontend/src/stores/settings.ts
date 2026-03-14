import { create } from "zustand";
import { persist } from "zustand/middleware";
import { config } from "@/config";

export type AudioFormat = "mp3" | "flac" | "ogg" | "m4a" | "opus" | "wav";
export type AudioQuality = "best" | "320k" | "256k" | "192k" | "128k";
export type OverwriteMode = "skip" | "force" | "metadata";
export type FilenameRestrict = "strict" | "loose" | null;
export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export interface ProviderPreference {
  id: string;
  enabled: boolean;
}

export type ProviderCategory = "audio" | "metadata" | "lyrics";

// Data shape — all persistable settings (no functions, no sync status)
export interface SettingsData {
  // Download settings
  audioFormat: AudioFormat;
  audioQuality: AudioQuality;
  bitrate: string;
  outputTemplate: string;
  outputDirectory: string;
  maxConcurrentDownloads: number;
  overwrite: OverwriteMode;
  maxFilenameLength: number;
  restrict: FilenameRestrict;

  // Metadata settings
  embedMetadata: boolean;
  embedLyrics: boolean;
  embedCover: boolean;
  id3Separator: string;

  // SponsorBlock
  sponsorBlock: boolean;

  // LRC / Lyrics files
  generateLrc: boolean;

  // M3U playlist generation
  m3u: string;

  // Archive (deduplication)
  archive: string;

  // Content filtering
  skipExplicit: boolean;
  scanForSongs: boolean;

  // Playlist options
  playlistNumbering: boolean;
  fetchAlbums: boolean;

  // Proxy
  proxy: string;

  // Custom arguments
  ffmpegArgs: string;
  ytDlpArgs: string;

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

  // Appearance settings
  compactSidebar: boolean;
  enableAnimations: boolean;
  reduceMotion: boolean;

  // Provider preferences
  audioSourcePreferences: ProviderPreference[];
  metadataSourcePreferences: ProviderPreference[];
  lyricsSourcePreferences: ProviderPreference[];
}

export interface SettingsState extends SettingsData {
  // Sync status (non-exportable)
  lastSyncedAt: string | null;
  isSyncing: boolean;

  // Actions
  update: <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => void;
  updateMany: (partial: Partial<SettingsData>) => void;
  reorderProvider: (category: ProviderCategory, fromIndex: number, toIndex: number) => void;
  toggleProvider: (category: ProviderCategory, id: string) => void;
  resetToDefaults: () => void;
  importSettings: (settings: Partial<SettingsState>) => void;
  exportSettings: () => SettingsData;
}

// Default provider preferences
const defaultAudioSourcePreferences: ProviderPreference[] = [
  { id: "youtube_music", enabled: true },
  { id: "youtube", enabled: true },
  { id: "soundcloud", enabled: false },
  { id: "bandcamp", enabled: false },
  { id: "piped", enabled: false },
];

const defaultMetadataSourcePreferences: ProviderPreference[] = [
  { id: "spotify", enabled: true },
  { id: "musicbrainz", enabled: true },
  { id: "discogs", enabled: true },
];

const defaultLyricsSourcePreferences: ProviderPreference[] = [
  { id: "synced", enabled: true },
  { id: "genius", enabled: true },
  { id: "musixmatch", enabled: true },
  { id: "azlyrics", enabled: false },
];

export const defaultSettings: SettingsData = {
  audioFormat: "mp3",
  audioQuality: "best",
  bitrate: "",
  outputTemplate: "{artist} - {title}",
  outputDirectory: "",
  maxConcurrentDownloads: 3,
  overwrite: "skip",
  maxFilenameLength: 255,
  restrict: null,
  embedMetadata: true,
  embedLyrics: true,
  embedCover: true,
  id3Separator: "/",
  sponsorBlock: false,
  generateLrc: false,
  m3u: "",
  archive: "",
  skipExplicit: false,
  scanForSongs: false,
  playlistNumbering: false,
  fetchAlbums: false,
  proxy: "",
  ffmpegArgs: "",
  ytDlpArgs: "",
  spotifyClientId: "",
  spotifyClientSecret: "",
  spotifyUserAuth: false,
  apiUrl: config.apiUrl,
  apiTimeout: 30,
  offlineMode: false,
  nameMatchThreshold: 60,
  artistMatchThreshold: 70,
  timeMatchThreshold: 25,
  logLevel: "INFO",
  cookieFile: "",
  compactSidebar: true,
  enableAnimations: true,
  reduceMotion: false,
  audioSourcePreferences: defaultAudioSourcePreferences,
  metadataSourcePreferences: defaultMetadataSourcePreferences,
  lyricsSourcePreferences: defaultLyricsSourcePreferences,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...defaultSettings,
      lastSyncedAt: null,
      isSyncing: false,

      update: (key, value) => set({ [key]: value } as Partial<SettingsState>),

      updateMany: (partial) => set(partial as Partial<SettingsState>),

      reorderProvider: (category, fromIndex, toIndex) => {
        const state = get();
        const keyMap: Record<ProviderCategory, keyof Pick<SettingsState, 'audioSourcePreferences' | 'metadataSourcePreferences' | 'lyricsSourcePreferences'>> = {
          audio: 'audioSourcePreferences',
          metadata: 'metadataSourcePreferences',
          lyrics: 'lyricsSourcePreferences',
        };
        const key = keyMap[category];
        const prefs = [...state[key]];
        const [removed] = prefs.splice(fromIndex, 1);
        prefs.splice(toIndex, 0, removed);
        set({ [key]: prefs });
      },

      toggleProvider: (category, id) => {
        const state = get();
        const keyMap: Record<ProviderCategory, keyof Pick<SettingsState, 'audioSourcePreferences' | 'metadataSourcePreferences' | 'lyricsSourcePreferences'>> = {
          audio: 'audioSourcePreferences',
          metadata: 'metadataSourcePreferences',
          lyrics: 'lyricsSourcePreferences',
        };
        const key = keyMap[category];
        const prefs = state[key].map((p) =>
          p.id === id ? { ...p, enabled: !p.enabled } : p
        );
        set({ [key]: prefs });
      },

      resetToDefaults: () => set({ ...defaultSettings, lastSyncedAt: null }),

      importSettings: (settings) => {
        const current = get();
        const exportableKeys = Object.keys(defaultSettings);
        const currentRecord = current as unknown as Record<string, unknown>;
        const settingsRecord = settings as unknown as Record<string, unknown>;
        const merged: Record<string, unknown> = {};
        for (const key of exportableKeys) {
          merged[key] = settingsRecord[key] ?? currentRecord[key];
        }
        set(merged as Partial<SettingsState>);
      },

      exportSettings: () => {
        const state = get();
        const exportableKeys = Object.keys(defaultSettings);
        const stateRecord = state as unknown as Record<string, unknown>;
        const exported: Record<string, unknown> = {};
        for (const key of exportableKeys) {
          exported[key] = stateRecord[key];
        }
        return exported as unknown as SettingsData;
      },
    }),
    {
      name: "spotdl-settings",
      merge: (persisted, current) => {
        if (!persisted || typeof persisted !== "object") {
          return current;
        }
        const exportableKeys = Object.keys(defaultSettings);
        const merged = { ...current } as Record<string, unknown>;
        for (const key of exportableKeys) {
          if (key in (persisted as Record<string, unknown>)) {
            merged[key] = (persisted as Record<string, unknown>)[key];
          }
        }
        return merged as unknown as SettingsState;
      },
    }
  )
);
