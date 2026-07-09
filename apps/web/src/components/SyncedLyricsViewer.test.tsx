import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { LyricsOut } from "../api/generated/types.gen";
import {
  activeLineIndex,
  parseLrc,
  SyncedLyricsViewer,
} from "./SyncedLyricsViewer";

function lyric(overrides: Partial<LyricsOut>): LyricsOut {
  return {
    id: "l1",
    kind: "synced",
    source: "lrclib",
    text: "",
    net_score: 0,
    upvotes: 0,
    downvotes: 0,
    ...overrides,
  };
}

const SYNCED_TEXT = "[00:00.00] one\n[00:05.00] two\n[00:10.00] three";

describe("parseLrc", () => {
  it("parses timestamps into ordered lines", () => {
    const lines = parseLrc(SYNCED_TEXT);
    expect(lines).toEqual([
      { timeMs: 0, text: "one" },
      { timeMs: 5000, text: "two" },
      { timeMs: 10000, text: "three" },
    ]);
  });

  it("returns null for text with no timestamps", () => {
    expect(parseLrc("just some plain words\nno stamps here")).toBeNull();
  });

  it("selects the last line whose stamp has passed", () => {
    const lines = parseLrc(SYNCED_TEXT)!;
    expect(activeLineIndex(lines, 0)).toBe(0);
    expect(activeLineIndex(lines, 4999)).toBe(0);
    expect(activeLineIndex(lines, 5000)).toBe(1);
    expect(activeLineIndex(lines, 999999)).toBe(2);
  });
});

describe("SyncedLyricsViewer", () => {
  beforeEach(() => {
    // jsdom doesn't implement scrollIntoView; stub it so we can assert on it.
    Element.prototype.scrollIntoView = vi.fn();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  it("advances the active line and autoscrolls it while playing", () => {
    render(<SyncedLyricsViewer lyrics={[lyric({ text: SYNCED_TEXT })]} />);

    expect(screen.getByText("one")).toHaveAttribute("data-active", "true");

    const scrollIntoView = Element.prototype.scrollIntoView as ReturnType<
      typeof vi.fn
    >;
    scrollIntoView.mockClear();

    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    act(() => vi.advanceTimersByTime(5000));

    expect(screen.getByText("two")).toHaveAttribute("data-active", "true");
    expect(screen.getByText("one")).toHaveAttribute("data-active", "false");
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it("disengages follow on manual scroll and stops autoscrolling", () => {
    render(<SyncedLyricsViewer lyrics={[lyric({ text: SYNCED_TEXT })]} />);
    // Let the mount autoscroll's guard-clearing timeout fire.
    act(() => vi.advanceTimersByTime(1));

    const follow = screen.getByRole("button", { name: "Follow" });
    expect(follow).toHaveAttribute("aria-pressed", "true");

    fireEvent.scroll(screen.getByTestId("lyrics-scroll"));
    expect(follow).toHaveAttribute("aria-pressed", "false");

    const scrollIntoView = Element.prototype.scrollIntoView as ReturnType<
      typeof vi.fn
    >;
    scrollIntoView.mockClear();

    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    act(() => vi.advanceTimersByTime(5000));

    // The line still advances, but with follow off there is no autoscroll.
    expect(screen.getByText("two")).toHaveAttribute("data-active", "true");
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it("falls back to a plain render for plain (and unstamped) variants", () => {
    render(
      <SyncedLyricsViewer
        lyrics={[lyric({ kind: "plain", text: "plain words here" })]}
      />,
    );
    expect(screen.getByText("plain words here")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Play" }),
    ).not.toBeInTheDocument();
  });
});
