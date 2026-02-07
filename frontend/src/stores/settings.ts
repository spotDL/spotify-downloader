import { create } from "zustand";
import { persist } from "zustand/middleware";

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

export interface SettingsState {
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

  // Sync status
  lastSyncedAt: string | null;
  isSyncing: boolean;

  // Actions - Download
  setAudioFormat: (format: AudioFormat) => void;
  setAudioQuality: (quality: AudioQuality) => void;
  setBitrate: (bitrate: string) => void;
  setOutputTemplate: (template: string) => void;
  setOutputDirectory: (directory: string) => void;
  setMaxConcurrentDownloads: (max: number) => void;
  setOverwrite: (mode: OverwriteMode) => void;
  setMaxFilenameLength: (length: number) => void;
  setRestrict: (mode: FilenameRestrict) => void;

  // Actions - Metadata
  setEmbedMetadata: (embed: boolean) => void;
  setEmbedLyrics: (embed: boolean) => void;
  setEmbedCover: (embed: boolean) => void;
  setId3Separator: (separator: string) => void;

  // Actions - Features
  setSponsorBlock: (enabled: boolean) => void;
  setGenerateLrc: (enabled: boolean) => void;
  setM3u: (template: string) => void;
  setArchive: (path: string) => void;
  setSkipExplicit: (skip: boolean) => void;
  setScanForSongs: (scan: boolean) => void;
  setPlaylistNumbering: (enabled: boolean) => void;
  setFetchAlbums: (enabled: boolean) => void;
  setProxy: (proxy: string) => void;
  setFfmpegArgs: (args: string) => void;
  setYtDlpArgs: (args: string) => void;

  // Actions - Credentials
  setSpotifyClientId: (id: string) => void;
  setSpotifyClientSecret: (secret: string) => void;
  setSpotifyUserAuth: (auth: boolean) => void;

  // Actions - Server
  setApiUrl: (url: string) => void;
  setApiTimeout: (timeout: number) => void;
  setOfflineMode: (offline: boolean) => void;

  // Actions - Matching
  setNameMatchThreshold: (threshold: number) => void;
  setArtistMatchThreshold: (threshold: number) => void;
  setTimeMatchThreshold: (threshold: number) => void;

  // Actions - Advanced
  setLogLevel: (level: LogLevel) => void;
  setCookieFile: (file: string) => void;

  // Actions - Appearance
  setCompactSidebar: (compact: boolean) => void;
  setEnableAnimations: (enable: boolean) => void;
  setReduceMotion: (reduce: boolean) => void;

  // Provider preference actions
  setAudioSourcePreferences: (prefs: ProviderPreference[]) => void;
  setMetadataSourcePreferences: (prefs: ProviderPreference[]) => void;
  setLyricsSourcePreferences: (prefs: ProviderPreference[]) => void;
  reorderProvider: (category: ProviderCategory, fromIndex: number, toIndex: number) => void;
  toggleProvider: (category: ProviderCategory, id: string) => void;

  resetToDefaults: () => void;
  setSyncing: (syncing: boolean) => void;
  setLastSyncedAt: (timestamp: string | null) => void;
  importSettings: (settings: Partial<SettingsState>) => void;
  exportSettings: () => ExportableSettings;
}

// Settings that can be exported/imported
export interface ExportableSettings {
  // Download
  audioFormat: AudioFormat;
  audioQuality: AudioQuality;
  bitrate: string;
  outputTemplate: string;
  outputDirectory: string;
  maxConcurrentDownloads: number;
  overwrite: OverwriteMode;
  maxFilenameLength: number;
  restrict: FilenameRestrict;

  // Metadata
  embedMetadata: boolean;
  embedLyrics: boolean;
  embedCover: boolean;
  id3Separator: string;

  // Features
  sponsorBlock: boolean;
  generateLrc: boolean;
  m3u: string;
  archive: string;
  skipExplicit: boolean;
  scanForSongs: boolean;
  playlistNumbering: boolean;
  fetchAlbums: boolean;
  proxy: string;
  ffmpegArgs: string;
  ytDlpArgs: string;

  // Credentials
  spotifyClientId: string;
  spotifyClientSecret: string;
  spotifyUserAuth: boolean;

  // Server
  apiUrl: string;
  apiTimeout: number;
  offlineMode: boolean;

  // Matching
  nameMatchThreshold: number;
  artistMatchThreshold: number;
  timeMatchThreshold: number;

  // Advanced
  logLevel: LogLevel;
  cookieFile: string;

  // Appearance
  compactSidebar: boolean;
  enableAnimations: boolean;
  reduceMotion: boolean;

  // Provider preferences
  audioSourcePreferences: ProviderPreference[];
  metadataSourcePreferences: ProviderPreference[];
  lyricsSourcePreferences: ProviderPreference[];
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

const defaultSettings: ExportableSettings = {
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
  apiUrl: "http://localhost:8000",
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

      // Download
      setAudioFormat: (format) => set({ audioFormat: format }),
      setAudioQuality: (quality) => set({ audioQuality: quality }),
      setBitrate: (bitrate) => set({ bitrate }),
      setOutputTemplate: (template) => set({ outputTemplate: template }),
      setOutputDirectory: (directory) => set({ outputDirectory: directory }),
      setMaxConcurrentDownloads: (max) => set({ maxConcurrentDownloads: max }),
      setOverwrite: (mode) => set({ overwrite: mode }),
      setMaxFilenameLength: (length) => set({ maxFilenameLength: length }),
      setRestrict: (mode) => set({ restrict: mode }),

      // Metadata
      setEmbedMetadata: (embed) => set({ embedMetadata: embed }),
      setEmbedLyrics: (embed) => set({ embedLyrics: embed }),
      setEmbedCover: (embed) => set({ embedCover: embed }),
      setId3Separator: (separator) => set({ id3Separator: separator }),

      // Features
      setSponsorBlock: (enabled) => set({ sponsorBlock: enabled }),
      setGenerateLrc: (enabled) => set({ generateLrc: enabled }),
      setM3u: (template) => set({ m3u: template }),
      setArchive: (path) => set({ archive: path }),
      setSkipExplicit: (skip) => set({ skipExplicit: skip }),
      setScanForSongs: (scan) => set({ scanForSongs: scan }),
      setPlaylistNumbering: (enabled) => set({ playlistNumbering: enabled }),
      setFetchAlbums: (enabled) => set({ fetchAlbums: enabled }),
      setProxy: (proxy) => set({ proxy }),
      setFfmpegArgs: (args) => set({ ffmpegArgs: args }),
      setYtDlpArgs: (args) => set({ ytDlpArgs: args }),

      // Credentials
      setSpotifyClientId: (id) => set({ spotifyClientId: id }),
      setSpotifyClientSecret: (secret) => set({ spotifyClientSecret: secret }),
      setSpotifyUserAuth: (auth) => set({ spotifyUserAuth: auth }),

      // Server
      setApiUrl: (url) => set({ apiUrl: url }),
      setApiTimeout: (timeout) => set({ apiTimeout: timeout }),
      setOfflineMode: (offline) => set({ offlineMode: offline }),

      // Matching
      setNameMatchThreshold: (threshold) => set({ nameMatchThreshold: threshold }),
      setArtistMatchThreshold: (threshold) => set({ artistMatchThreshold: threshold }),
      setTimeMatchThreshold: (threshold) => set({ timeMatchThreshold: threshold }),

      // Advanced
      setLogLevel: (level) => set({ logLevel: level }),
      setCookieFile: (file) => set({ cookieFile: file }),

      // Appearance
      setCompactSidebar: (compact) => set({ compactSidebar: compact }),
      setEnableAnimations: (enable) => set({ enableAnimations: enable }),
      setReduceMotion: (reduce) => set({ reduceMotion: reduce }),
      setSyncing: (syncing) => set({ isSyncing: syncing }),
      setLastSyncedAt: (timestamp) => set({ lastSyncedAt: timestamp }),

      // Provider preference actions
      setAudioSourcePreferences: (prefs) => set({ audioSourcePreferences: prefs }),
      setMetadataSourcePreferences: (prefs) => set({ metadataSourcePreferences: prefs }),
      setLyricsSourcePreferences: (prefs) => set({ lyricsSourcePreferences: prefs }),

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
        const merged: Record<string, unknown> = {};
        for (const key of Object.keys(defaultSettings)) {
          merged[key] = (settings as Record<string, unknown>)[key] ?? (current as Record<string, unknown>)[key];
        }
        set(merged);
      },

      exportSettings: () => {
        const state = get();
        const exported: Record<string, unknown> = {};
        for (const key of Object.keys(defaultSettings)) {
          exported[key] = (state as Record<string, unknown>)[key];
        }
        return exported as ExportableSettings;
      },
    }),
    {
      name: "spotdl-settings",
    }
  )
);
