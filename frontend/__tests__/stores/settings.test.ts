import { describe, it, expect, beforeEach } from "vitest";
import { useSettingsStore } from "../../src/stores/settings";

describe("useSettingsStore", () => {
  beforeEach(() => {
    // Reset store to defaults before each test
    useSettingsStore.getState().resetToDefaults();
  });

  it("should have correct default values", () => {
    const state = useSettingsStore.getState();

    expect(state.audioFormat).toBe("mp3");
    expect(state.audioQuality).toBe("best");
    expect(state.bitrate).toBe("");
    expect(state.outputTemplate).toBe("{artist} - {title}");
    expect(state.maxConcurrentDownloads).toBe(3);
    expect(state.overwrite).toBe("skip");
    expect(state.maxFilenameLength).toBe(255);
    expect(state.restrict).toBeNull();
    expect(state.embedMetadata).toBe(true);
    expect(state.embedLyrics).toBe(true);
    expect(state.embedCover).toBe(true);
    expect(state.id3Separator).toBe("/");
    expect(state.sponsorBlock).toBe(false);
    expect(state.generateLrc).toBe(false);
    expect(state.m3u).toBe("");
    expect(state.archive).toBe("");
    expect(state.skipExplicit).toBe(false);
    expect(state.scanForSongs).toBe(false);
    expect(state.playlistNumbering).toBe(false);
    expect(state.fetchAlbums).toBe(false);
    expect(state.proxy).toBe("");
    expect(state.ffmpegArgs).toBe("");
    expect(state.ytDlpArgs).toBe("");
    expect(state.apiUrl).toBe("http://localhost:8000");
    expect(state.offlineMode).toBe(false);
  });

  it("should update audio format", () => {
    useSettingsStore.getState().setAudioFormat("flac");
    expect(useSettingsStore.getState().audioFormat).toBe("flac");
  });

  it("should update audio quality", () => {
    useSettingsStore.getState().setAudioQuality("320k");
    expect(useSettingsStore.getState().audioQuality).toBe("320k");
  });

  it("should update bitrate", () => {
    useSettingsStore.getState().setBitrate("256k");
    expect(useSettingsStore.getState().bitrate).toBe("256k");
  });

  it("should update output template", () => {
    useSettingsStore.getState().setOutputTemplate("{title} - {artist}");
    expect(useSettingsStore.getState().outputTemplate).toBe("{title} - {artist}");
  });

  it("should update max concurrent downloads", () => {
    useSettingsStore.getState().setMaxConcurrentDownloads(5);
    expect(useSettingsStore.getState().maxConcurrentDownloads).toBe(5);
  });

  it("should update overwrite mode", () => {
    useSettingsStore.getState().setOverwrite("force");
    expect(useSettingsStore.getState().overwrite).toBe("force");

    useSettingsStore.getState().setOverwrite("metadata");
    expect(useSettingsStore.getState().overwrite).toBe("metadata");

    useSettingsStore.getState().setOverwrite("skip");
    expect(useSettingsStore.getState().overwrite).toBe("skip");
  });

  it("should update filename settings", () => {
    useSettingsStore.getState().setMaxFilenameLength(200);
    expect(useSettingsStore.getState().maxFilenameLength).toBe(200);

    useSettingsStore.getState().setRestrict("strict");
    expect(useSettingsStore.getState().restrict).toBe("strict");

    useSettingsStore.getState().setRestrict("loose");
    expect(useSettingsStore.getState().restrict).toBe("loose");

    useSettingsStore.getState().setRestrict(null);
    expect(useSettingsStore.getState().restrict).toBeNull();
  });

  it("should toggle metadata settings", () => {
    useSettingsStore.getState().setEmbedMetadata(false);
    useSettingsStore.getState().setEmbedLyrics(false);
    useSettingsStore.getState().setEmbedCover(false);

    const state = useSettingsStore.getState();
    expect(state.embedMetadata).toBe(false);
    expect(state.embedLyrics).toBe(false);
    expect(state.embedCover).toBe(false);
  });

  it("should update ID3 separator", () => {
    useSettingsStore.getState().setId3Separator("; ");
    expect(useSettingsStore.getState().id3Separator).toBe("; ");
  });

  it("should toggle download feature settings", () => {
    useSettingsStore.getState().setSponsorBlock(true);
    expect(useSettingsStore.getState().sponsorBlock).toBe(true);

    useSettingsStore.getState().setGenerateLrc(true);
    expect(useSettingsStore.getState().generateLrc).toBe(true);

    useSettingsStore.getState().setSkipExplicit(true);
    expect(useSettingsStore.getState().skipExplicit).toBe(true);

    useSettingsStore.getState().setScanForSongs(true);
    expect(useSettingsStore.getState().scanForSongs).toBe(true);

    useSettingsStore.getState().setPlaylistNumbering(true);
    expect(useSettingsStore.getState().playlistNumbering).toBe(true);

    useSettingsStore.getState().setFetchAlbums(true);
    expect(useSettingsStore.getState().fetchAlbums).toBe(true);
  });

  it("should update string-based feature settings", () => {
    useSettingsStore.getState().setM3u("{list}.m3u8");
    expect(useSettingsStore.getState().m3u).toBe("{list}.m3u8");

    useSettingsStore.getState().setArchive("archive.txt");
    expect(useSettingsStore.getState().archive).toBe("archive.txt");

    useSettingsStore.getState().setProxy("socks5://127.0.0.1:1080");
    expect(useSettingsStore.getState().proxy).toBe("socks5://127.0.0.1:1080");

    useSettingsStore.getState().setFfmpegArgs("-ac 2");
    expect(useSettingsStore.getState().ffmpegArgs).toBe("-ac 2");

    useSettingsStore.getState().setYtDlpArgs("--no-check-certificate");
    expect(useSettingsStore.getState().ytDlpArgs).toBe("--no-check-certificate");
  });

  it("should update API URL", () => {
    useSettingsStore.getState().setApiUrl("http://example.com:8080");
    expect(useSettingsStore.getState().apiUrl).toBe("http://example.com:8080");
  });

  it("should toggle offline mode", () => {
    useSettingsStore.getState().setOfflineMode(true);
    expect(useSettingsStore.getState().offlineMode).toBe(true);
  });

  it("should reset to defaults", () => {
    // Change some values
    useSettingsStore.getState().setAudioFormat("flac");
    useSettingsStore.getState().setAudioQuality("192k");
    useSettingsStore.getState().setEmbedMetadata(false);
    useSettingsStore.getState().setOverwrite("force");
    useSettingsStore.getState().setSponsorBlock(true);
    useSettingsStore.getState().setGenerateLrc(true);

    // Reset
    useSettingsStore.getState().resetToDefaults();

    const state = useSettingsStore.getState();
    expect(state.audioFormat).toBe("mp3");
    expect(state.audioQuality).toBe("best");
    expect(state.embedMetadata).toBe(true);
    expect(state.overwrite).toBe("skip");
    expect(state.sponsorBlock).toBe(false);
    expect(state.generateLrc).toBe(false);
  });

  it("should export and import settings", () => {
    // Change some settings
    useSettingsStore.getState().setAudioFormat("flac");
    useSettingsStore.getState().setOverwrite("metadata");
    useSettingsStore.getState().setSponsorBlock(true);

    // Export
    const exported = useSettingsStore.getState().exportSettings();
    expect(exported.audioFormat).toBe("flac");
    expect(exported.overwrite).toBe("metadata");
    expect(exported.sponsorBlock).toBe(true);

    // Reset and re-import
    useSettingsStore.getState().resetToDefaults();
    expect(useSettingsStore.getState().audioFormat).toBe("mp3");

    useSettingsStore.getState().importSettings(exported);
    expect(useSettingsStore.getState().audioFormat).toBe("flac");
    expect(useSettingsStore.getState().overwrite).toBe("metadata");
    expect(useSettingsStore.getState().sponsorBlock).toBe(true);
  });
});
