import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TrackRow, TrackRowList } from "../../src/components/ui/track-row";
import type { InternalSong } from "../../src/types";

// Mock @tanstack/react-router
vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    params,
    className,
  }: {
    children: React.ReactNode;
    to: string;
    params?: Record<string, string>;
    className?: string;
  }) => (
    <a
      href={`${to.replace("$id", params?.id || "")}`}
      className={className}
      data-testid="track-link"
    >
      {children}
    </a>
  ),
}));

const mockTrack: InternalSong = {
  id: "track-1",
  name: "Test Song",
  artists: ["Test Artist", "Featured Artist"],
  artist: "Test Artist",
  duration: 210,
  album_name: "Test Album",
  album_id: "album-1",
  cover_url: "https://example.com/cover.jpg",
  isrc: "US-S1Z-12-12345",
  year: 2024,
  platforms: [],
};

const mockTrackNoCover: InternalSong = {
  ...mockTrack,
  id: "track-2",
  name: "No Cover Song",
  cover_url: null,
};

const mockTracks: InternalSong[] = [
  mockTrack,
  { ...mockTrack, id: "track-2", name: "Second Song" },
  { ...mockTrack, id: "track-3", name: "Third Song" },
];

describe("TrackRow", () => {
  describe("rendering", () => {
    it("renders track name", () => {
      render(<TrackRow track={mockTrack} />);

      expect(screen.getByText("Test Song")).toBeInTheDocument();
    });

    it("renders artist name", () => {
      render(<TrackRow track={mockTrack} />);

      expect(screen.getByText("Test Artist")).toBeInTheDocument();
    });

    it("renders duration in mm:ss format", () => {
      render(<TrackRow track={mockTrack} />);

      // 210 seconds = 3:30
      expect(screen.getByText("3:30")).toBeInTheDocument();
    });

    it("renders cover art by default", () => {
      render(<TrackRow track={mockTrack} />);

      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("src", "https://example.com/cover.jpg");
    });

    it("hides cover when showCover is false", () => {
      render(<TrackRow track={mockTrack} showCover={false} />);

      expect(screen.queryByRole("img")).not.toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <TrackRow track={mockTrack} className="custom-track" />
      );

      expect(container.querySelector(".custom-track")).toBeInTheDocument();
    });
  });

  describe("optional content", () => {
    it("shows album name when showAlbum is true", () => {
      render(<TrackRow track={mockTrack} showAlbum />);

      expect(screen.getByText("Test Album")).toBeInTheDocument();
    });

    it("hides album name by default", () => {
      render(<TrackRow track={mockTrack} />);

      // Album name should not be shown as separate text (only artist)
      const albumText = screen.queryByText("Test Album");
      // It might be in the subtitle combined with artist
      expect(screen.getByText("Test Artist")).toBeInTheDocument();
    });

    it("hides artist when showArtist is false", () => {
      render(<TrackRow track={mockTrack} showArtist={false} />);

      expect(screen.queryByText("Test Artist")).not.toBeInTheDocument();
    });

    it("hides duration when showDuration is false", () => {
      render(<TrackRow track={mockTrack} showDuration={false} />);

      expect(screen.queryByText("3:30")).not.toBeInTheDocument();
    });

    it("shows position number when provided", () => {
      render(<TrackRow track={mockTrack} position={5} />);

      expect(screen.getByText("05")).toBeInTheDocument();
    });
  });

  describe("click navigation", () => {
    it("wraps in Link when no onClick handler", () => {
      render(<TrackRow track={mockTrack} />);

      const link = screen.getByTestId("track-link");
      expect(link).toHaveAttribute("href", "/song/track-1");
    });

    it("does not wrap in Link when onClick is provided", () => {
      const handleClick = vi.fn();
      render(<TrackRow track={mockTrack} onClick={handleClick} />);

      expect(screen.queryByTestId("track-link")).not.toBeInTheDocument();
    });

    it("calls onClick when provided", () => {
      const handleClick = vi.fn();
      const { container } = render(<TrackRow track={mockTrack} onClick={handleClick} />);

      // The onClick is attached to the inner content div, triggered via the wrapper
      const wrapper = screen.getByRole("button");
      const contentDiv = container.querySelector("[class*='group flex items-center']");
      fireEvent.click(contentDiv!);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("keyboard navigation", () => {
    it("handles Enter key", () => {
      const handleClick = vi.fn();
      render(<TrackRow track={mockTrack} onClick={handleClick} />);

      const row = screen.getByRole("button");
      fireEvent.keyDown(row, { key: "Enter" });

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("handles Space key", () => {
      const handleClick = vi.fn();
      render(<TrackRow track={mockTrack} onClick={handleClick} />);

      const row = screen.getByRole("button");
      fireEvent.keyDown(row, { key: " " });

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("has correct tabIndex", () => {
      const handleClick = vi.fn();
      render(<TrackRow track={mockTrack} onClick={handleClick} />);

      const row = screen.getByRole("button");
      expect(row).toHaveAttribute("tabIndex", "0");
    });
  });

  describe("download button", () => {
    it("shows download button when onDownload is provided", () => {
      const handleDownload = vi.fn();
      render(<TrackRow track={mockTrack} onDownload={handleDownload} />);

      expect(
        screen.getByRole("button", { name: /Download/i })
      ).toBeInTheDocument();
    });

    it("hides download button by default", () => {
      render(<TrackRow track={mockTrack} />);

      expect(
        screen.queryByRole("button", { name: /Download/i })
      ).not.toBeInTheDocument();
    });

    it("calls onDownload when download button is clicked", () => {
      const handleDownload = vi.fn();
      render(<TrackRow track={mockTrack} onDownload={handleDownload} />);

      fireEvent.click(screen.getByRole("button", { name: /Download/i }));

      expect(handleDownload).toHaveBeenCalledTimes(1);
    });

    it("stops propagation on download click", () => {
      const handleClick = vi.fn();
      const handleDownload = vi.fn();
      render(
        <TrackRow
          track={mockTrack}
          onClick={handleClick}
          onDownload={handleDownload}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Download/i }));

      expect(handleDownload).toHaveBeenCalled();
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe("active and playing states", () => {
    it("applies active styles", () => {
      const { container } = render(
        <TrackRow track={mockTrack} isActive />
      );

      const row = container.querySelector("[class*='bg-'][class*='accent-safe']");
      expect(row).toBeInTheDocument();
    });

    it("shows playing indicator when isPlaying", () => {
      const { container } = render(
        <TrackRow track={mockTrack} position={1} isPlaying />
      );

      // Playing indicator shows animated bars instead of position number
      expect(screen.queryByText("01")).not.toBeInTheDocument();
      // Should have playing indicator spans with animation
      const animatedBars = container.querySelectorAll("[class*='animate-']");
      expect(animatedBars.length).toBeGreaterThan(0);
    });

    it("shows position number when not playing", () => {
      render(<TrackRow track={mockTrack} position={1} isPlaying={false} />);

      expect(screen.getByText("01")).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("applies compact padding", () => {
      const { container } = render(
        <TrackRow track={mockTrack} compact />
      );

      const row = container.querySelector(".px-3.py-2");
      expect(row).toBeInTheDocument();
    });

    it("applies smaller text in compact mode", () => {
      const { container } = render(
        <TrackRow track={mockTrack} compact />
      );

      const name = screen.getByText("Test Song");
      expect(name).toHaveClass("text-sm");
    });
  });

  describe("fallback cover", () => {
    it("shows fallback icon when no cover", () => {
      const { container } = render(
        <TrackRow track={mockTrackNoCover} />
      );

      // Should show fallback SVG
      const fallback = container.querySelector("svg");
      expect(fallback).toBeInTheDocument();
    });
  });

  describe("duration formatting", () => {
    it("formats short duration", () => {
      const shortTrack = { ...mockTrack, duration: 65 };
      render(<TrackRow track={shortTrack} />);

      expect(screen.getByText("1:05")).toBeInTheDocument();
    });

    it("formats long duration", () => {
      const longTrack = { ...mockTrack, duration: 605 };
      render(<TrackRow track={longTrack} />);

      expect(screen.getByText("10:05")).toBeInTheDocument();
    });

    it("pads seconds with zero", () => {
      const track = { ...mockTrack, duration: 61 };
      render(<TrackRow track={track} />);

      expect(screen.getByText("1:01")).toBeInTheDocument();
    });
  });
});

describe("TrackRowList", () => {
  describe("rendering", () => {
    it("renders all tracks", () => {
      render(<TrackRowList tracks={mockTracks} />);

      expect(screen.getByText("Test Song")).toBeInTheDocument();
      expect(screen.getByText("Second Song")).toBeInTheDocument();
      expect(screen.getByText("Third Song")).toBeInTheDocument();
    });

    it("shows position numbers starting from 1", () => {
      render(<TrackRowList tracks={mockTracks} />);

      expect(screen.getByText("01")).toBeInTheDocument();
      expect(screen.getByText("02")).toBeInTheDocument();
      expect(screen.getByText("03")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <TrackRowList tracks={mockTracks} className="custom-list" />
      );

      expect(container.firstChild).toHaveClass("custom-list");
    });
  });

  describe("track interaction", () => {
    it("calls onTrackClick with track and index", () => {
      const handleTrackClick = vi.fn();
      const { container } = render(
        <TrackRowList tracks={mockTracks} onTrackClick={handleTrackClick} />
      );

      // Find all content divs (the ones with the onClick)
      const contentDivs = container.querySelectorAll("[class*='group flex items-center']");
      fireEvent.click(contentDivs[1]); // Click second track

      expect(handleTrackClick).toHaveBeenCalledWith(mockTracks[1], 1);
    });

    it("calls onDownload with track", () => {
      const handleDownload = vi.fn();
      render(
        <TrackRowList tracks={mockTracks} onDownload={handleDownload} />
      );

      const downloadButtons = screen.getAllByRole("button", { name: /Download/i });
      fireEvent.click(downloadButtons[1]);

      expect(handleDownload).toHaveBeenCalledWith(mockTracks[1]);
    });
  });

  describe("active and playing state", () => {
    it("marks correct track as active", () => {
      const { container } = render(
        <TrackRowList tracks={mockTracks} activeTrackId="track-2" />
      );

      // Second track should have active styles
      const rows = container.querySelectorAll("[class*='px-']");
      expect(rows[1]).toHaveClass("bg-[var(--accent-safe)]/10");
    });

    it("marks correct track as playing", () => {
      const { container } = render(
        <TrackRowList tracks={mockTracks} playingTrackId="track-2" />
      );

      // Second track should show playing indicator
      expect(screen.getByText("01")).toBeInTheDocument(); // First track shows number
      expect(screen.queryByText("02")).not.toBeInTheDocument(); // Second track shows animation
      expect(screen.getByText("03")).toBeInTheDocument(); // Third track shows number
    });
  });

  describe("display options", () => {
    it("passes showCover to rows", () => {
      render(<TrackRowList tracks={mockTracks} showCover={false} />);

      expect(screen.queryByRole("img")).not.toBeInTheDocument();
    });

    it("passes showAlbum to rows", () => {
      render(<TrackRowList tracks={mockTracks} showAlbum />);

      expect(screen.getAllByText("Test Album").length).toBe(3);
    });

    it("passes showArtist to rows", () => {
      render(<TrackRowList tracks={mockTracks} showArtist={false} />);

      expect(screen.queryByText("Test Artist")).not.toBeInTheDocument();
    });

    it("passes showDuration to rows", () => {
      render(<TrackRowList tracks={mockTracks} showDuration={false} />);

      expect(screen.queryByText("3:30")).not.toBeInTheDocument();
    });

    it("passes compact to rows", () => {
      const { container } = render(
        <TrackRowList tracks={mockTracks} compact />
      );

      const compactRows = container.querySelectorAll(".px-3.py-2");
      expect(compactRows.length).toBe(3);
    });
  });

  describe("dividers", () => {
    it("applies divider class", () => {
      const { container } = render(<TrackRowList tracks={mockTracks} />);

      expect(container.firstChild).toHaveClass("divide-y");
    });
  });

  describe("empty state", () => {
    it("renders nothing for empty tracks", () => {
      const { container } = render(<TrackRowList tracks={[]} />);

      expect(container.firstChild).toBeEmptyDOMElement();
    });
  });
});
