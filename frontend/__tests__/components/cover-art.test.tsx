import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CoverArt } from "../../src/components/ui/cover-art";

describe("CoverArt", () => {
  describe("rendering", () => {
    it("renders with image when src is provided", () => {
      render(<CoverArt src="https://example.com/image.jpg" alt="Test Album" />);

      const img = screen.getByRole("img");
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "https://example.com/image.jpg");
      expect(img).toHaveAttribute("alt", "Test Album");
    });

    it("renders fallback when src is null", () => {
      const { container } = render(<CoverArt src={null} alt="Test Album" />);

      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      // Should show fallback icon (SVG within the fallback div)
      const fallbackIcon = container.querySelector("svg");
      expect(fallbackIcon).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" className="custom-class" />
      );

      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("sizes", () => {
    it("applies xs size class", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" size="xs" />
      );
      expect(container.firstChild).toHaveClass("w-12", "h-12");
    });

    it("applies sm size class", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" size="sm" />
      );
      expect(container.firstChild).toHaveClass("w-14", "h-14");
    });

    it("applies md size class (default)", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" />
      );
      expect(container.firstChild).toHaveClass("w-20", "h-20");
    });

    it("applies lg size class", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" size="lg" />
      );
      expect(container.firstChild).toHaveClass("w-[150px]", "h-[150px]");
    });

    it("applies xl size class", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" size="xl" />
      );
      expect(container.firstChild).toHaveClass("w-[200px]", "h-[200px]");
    });

    it("applies 2xl size class", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" size="2xl" />
      );
      expect(container.firstChild).toHaveClass("w-[300px]", "h-[300px]");
    });

    it("applies hero size class", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" size="hero" />
      );
      expect(container.firstChild).toHaveClass("w-[400px]", "h-[400px]");
    });
  });

  describe("shapes", () => {
    it("applies rounded shape (default)", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" />
      );
      expect(container.firstChild).toHaveClass("rounded-xl");
    });

    it("applies circle shape", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" shape="circle" />
      );
      expect(container.firstChild).toHaveClass("rounded-full");
    });
  });

  describe("fallback icons", () => {
    it("shows artist fallback icon", () => {
      const { container } = render(
        <CoverArt src={null} alt="Artist" fallbackIcon="artist" />
      );
      // Should show fallback div with SVG
      const fallbackDiv = container.querySelector("svg");
      expect(fallbackDiv).toBeInTheDocument();
    });

    it("shows album fallback icon", () => {
      const { container } = render(
        <CoverArt src={null} alt="Album" fallbackIcon="album" />
      );
      const fallbackDiv = container.querySelector("svg");
      expect(fallbackDiv).toBeInTheDocument();
    });

    it("shows playlist fallback icon", () => {
      const { container } = render(
        <CoverArt src={null} alt="Playlist" fallbackIcon="playlist" />
      );
      const fallbackDiv = container.querySelector("svg");
      expect(fallbackDiv).toBeInTheDocument();
    });

    it("shows track fallback icon by default", () => {
      const { container } = render(
        <CoverArt src={null} alt="Track" />
      );
      const fallbackDiv = container.querySelector("svg");
      expect(fallbackDiv).toBeInTheDocument();
    });
  });

  describe("image loading states", () => {
    it("shows shimmer loading state while image is loading", () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" />
      );

      // Before onLoad, shimmer should be visible
      const shimmer = container.querySelector(".shimmer");
      expect(shimmer).toBeInTheDocument();
    });

    it("hides shimmer after image loads", async () => {
      const { container } = render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" />
      );

      const img = screen.getByRole("img");
      fireEvent.load(img);

      await waitFor(() => {
        expect(img).toHaveClass("opacity-100");
      });
    });

    it("shows fallback on image error", async () => {
      const { container } = render(
        <CoverArt src="https://example.com/broken-image.jpg" alt="Test" />
      );

      const img = screen.getByRole("img");
      fireEvent.error(img);

      await waitFor(() => {
        // Image should be hidden and fallback should be shown
        const fallbackIcon = container.querySelector("svg");
        expect(fallbackIcon).toBeInTheDocument();
      });
    });
  });

  describe("play button", () => {
    it("does not show play button by default", () => {
      render(<CoverArt src="https://example.com/image.jpg" alt="Test" />);

      expect(screen.queryByLabelText(/Play/)).not.toBeInTheDocument();
    });

    it("shows play button when showPlayButton is true and onPlay is provided", () => {
      const handlePlay = vi.fn();
      render(
        <CoverArt
          src="https://example.com/image.jpg"
          alt="Test Album"
          showPlayButton
          onPlay={handlePlay}
        />
      );

      expect(screen.getByLabelText("Play Test Album")).toBeInTheDocument();
    });

    it("does not show play button when only showPlayButton is true without onPlay", () => {
      render(
        <CoverArt
          src="https://example.com/image.jpg"
          alt="Test Album"
          showPlayButton
        />
      );

      expect(screen.queryByLabelText(/Play/)).not.toBeInTheDocument();
    });

    it("calls onPlay when play button is clicked", () => {
      const handlePlay = vi.fn();
      render(
        <CoverArt
          src="https://example.com/image.jpg"
          alt="Test Album"
          showPlayButton
          onPlay={handlePlay}
        />
      );

      fireEvent.click(screen.getByLabelText("Play Test Album"));
      expect(handlePlay).toHaveBeenCalledTimes(1);
    });

    it("stops event propagation when play button is clicked", () => {
      const handlePlay = vi.fn();
      const handleContainerClick = vi.fn();

      render(
        <div onClick={handleContainerClick}>
          <CoverArt
            src="https://example.com/image.jpg"
            alt="Test Album"
            showPlayButton
            onPlay={handlePlay}
          />
        </div>
      );

      fireEvent.click(screen.getByLabelText("Play Test Album"));

      expect(handlePlay).toHaveBeenCalledTimes(1);
      // Should stop propagation
      expect(handleContainerClick).not.toHaveBeenCalled();
    });

    it("has correct aria-label for play button", () => {
      const handlePlay = vi.fn();
      render(
        <CoverArt
          src="https://example.com/image.jpg"
          alt="My Album"
          showPlayButton
          onPlay={handlePlay}
        />
      );

      const playButton = screen.getByRole("button");
      expect(playButton).toHaveAttribute("aria-label", "Play My Album");
    });
  });

  describe("lazy loading", () => {
    it("has lazy loading attribute", () => {
      render(
        <CoverArt src="https://example.com/image.jpg" alt="Test" />
      );

      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("loading", "lazy");
    });
  });
});
