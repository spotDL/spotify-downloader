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
    expect(state.outputTemplate).toBe("{artist} - {title}");
    expect(state.maxConcurrentDownloads).toBe(3);
    expect(state.overwriteExisting).toBe(false);
    expect(state.embedMetadata).toBe(true);
    expect(state.embedLyrics).toBe(true);
    expect(state.embedCoverArt).toBe(true);
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

  it("should update output template", () => {
    useSettingsStore.getState().setOutputTemplate("{title} - {artist}");
    expect(useSettingsStore.getState().outputTemplate).toBe("{title} - {artist}");
  });

  it("should update max concurrent downloads", () => {
    useSettingsStore.getState().setMaxConcurrentDownloads(5);
    expect(useSettingsStore.getState().maxConcurrentDownloads).toBe(5);
  });

  it("should toggle overwrite existing", () => {
    useSettingsStore.getState().setOverwriteExisting(true);
    expect(useSettingsStore.getState().overwriteExisting).toBe(true);
  });

  it("should toggle metadata settings", () => {
    useSettingsStore.getState().setEmbedMetadata(false);
    useSettingsStore.getState().setEmbedLyrics(false);
    useSettingsStore.getState().setEmbedCoverArt(false);

    const state = useSettingsStore.getState();
    expect(state.embedMetadata).toBe(false);
    expect(state.embedLyrics).toBe(false);
    expect(state.embedCoverArt).toBe(false);
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

    // Reset
    useSettingsStore.getState().resetToDefaults();

    const state = useSettingsStore.getState();
    expect(state.audioFormat).toBe("mp3");
    expect(state.audioQuality).toBe("best");
    expect(state.embedMetadata).toBe(true);
  });
});
