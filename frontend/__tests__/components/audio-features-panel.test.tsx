import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  AudioFeaturesPanel,
  AudioFeaturesSummary,
  SingleFeature,
} from "../../src/components/ui/audio-features-panel";
import type { AudioFeatures } from "../../src/types";

const mockFeatures: AudioFeatures = {
  bpm: 120,
  energy: 0.8,
  danceability: 0.75,
  valence: 0.6,
  key: 5,
  mode: 1,
  loudness: -5.5,
  speechiness: 0.1,
  acousticness: 0.2,
  instrumentalness: 0.01,
  liveness: 0.15,
  time_signature: 4,
};

const nullFeatures: AudioFeatures = {
  bpm: null,
  energy: null,
  danceability: null,
  valence: null,
  key: null,
  mode: null,
  loudness: null,
  speechiness: null,
  acousticness: null,
  instrumentalness: null,
  liveness: null,
  time_signature: null,
};

const partialFeatures: AudioFeatures = {
  bpm: 100,
  energy: 0.5,
  danceability: null,
  valence: 0.3,
  key: 2,
  mode: 0,
  loudness: null,
  speechiness: 0.05,
  acousticness: null,
  instrumentalness: 0.9,
  liveness: null,
  time_signature: 3,
};

describe("AudioFeaturesPanel", () => {
  describe("rendering", () => {
    it("renders all feature bars in full variant", () => {
      render(<AudioFeaturesPanel features={mockFeatures} />);

      expect(screen.getByText("Energy")).toBeInTheDocument();
      expect(screen.getByText("Danceability")).toBeInTheDocument();
      expect(screen.getByText("Valence")).toBeInTheDocument();
      expect(screen.getByText("Speechiness")).toBeInTheDocument();
      expect(screen.getByText("Acousticness")).toBeInTheDocument();
      expect(screen.getByText("Instrumentalness")).toBeInTheDocument();
      expect(screen.getByText("Liveness")).toBeInTheDocument();
    });

    it("renders compact feature bars", () => {
      render(<AudioFeaturesPanel features={mockFeatures} variant="compact" />);

      // Compact only shows 4 features
      expect(screen.getByText("Energy")).toBeInTheDocument();
      expect(screen.getByText("Danceability")).toBeInTheDocument();
      expect(screen.getByText("Valence")).toBeInTheDocument();
      expect(screen.getByText("Acousticness")).toBeInTheDocument();

      // Should not show these in compact
      expect(screen.queryByText("Speechiness")).not.toBeInTheDocument();
      expect(screen.queryByText("Liveness")).not.toBeInTheDocument();
    });

    it("shows more features hint in compact mode", () => {
      render(<AudioFeaturesPanel features={mockFeatures} variant="compact" />);

      expect(screen.getByText(/more features available/)).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <AudioFeaturesPanel features={mockFeatures} className="custom-panel" />
      );

      expect(container.firstChild).toHaveClass("custom-panel");
    });
  });

  describe("tempo display", () => {
    it("shows BPM value", () => {
      render(<AudioFeaturesPanel features={mockFeatures} />);

      expect(screen.getByText("120")).toBeInTheDocument();
    });

    it("shows tempo visualizer in full variant", () => {
      render(<AudioFeaturesPanel features={mockFeatures} variant="full" />);

      // Full variant shows BPM label
      expect(screen.getByText("BPM")).toBeInTheDocument();
      expect(screen.getByText("120")).toBeInTheDocument();
    });
  });

  describe("key signature display", () => {
    it("shows key signature badge", () => {
      const { container } = render(
        <AudioFeaturesPanel features={mockFeatures} />
      );

      // Key 5 with mode 1 (major) = F Major
      const keyBadge = container.querySelector(".key-signature-badge, [title*='Key']");
      expect(keyBadge || screen.queryByText(/F/)).toBeTruthy();
    });
  });

  describe("time signature display", () => {
    it("shows time signature", () => {
      render(<AudioFeaturesPanel features={mockFeatures} />);

      expect(screen.getByText("4/4")).toBeInTheDocument();
    });

    it("handles null time signature", () => {
      render(<AudioFeaturesPanel features={nullFeatures} />);

      expect(screen.getByText("--/4")).toBeInTheDocument();
    });
  });

  describe("loudness display", () => {
    it("shows loudness in full variant", () => {
      render(<AudioFeaturesPanel features={mockFeatures} variant="full" />);

      // Loudness is rounded: -5.5 -> -5 or -6
      expect(screen.getByText("dB", { exact: false })).toBeInTheDocument();
    });

    it("does not show loudness in compact variant", () => {
      const { container } = render(<AudioFeaturesPanel features={mockFeatures} variant="compact" />);

      // In compact mode, the loudness element should not be present
      const loudnessElements = container.querySelectorAll("[title='Average Loudness (dB)']");
      expect(loudnessElements.length).toBe(0);
    });

    it("handles null loudness", () => {
      const { container } = render(<AudioFeaturesPanel features={nullFeatures} variant="full" />);

      const loudnessElements = container.querySelectorAll("[title='Average Loudness (dB)']");
      expect(loudnessElements.length).toBe(0);
    });
  });

  describe("feature bars", () => {
    it("shows percentage values", () => {
      render(<AudioFeaturesPanel features={mockFeatures} />);

      // Energy is 0.8 = 80%
      expect(screen.getByText("80%")).toBeInTheDocument();
      // Danceability is 0.75 = 75%
      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    it("handles null values with dashes", () => {
      render(<AudioFeaturesPanel features={partialFeatures} />);

      // Some values should show as "--"
      const dashes = screen.getAllByText("--");
      expect(dashes.length).toBeGreaterThan(0);
    });

    it("applies color based on intensity", () => {
      const { container } = render(
        <AudioFeaturesPanel features={mockFeatures} />
      );

      // High values (>66%) should have different colors than low values (<33%)
      const bars = container.querySelectorAll(".h-1\\.5 > div");
      expect(bars.length).toBeGreaterThan(0);
    });
  });

  describe("feature tooltips", () => {
    it("has title attributes for tooltips", () => {
      const { container } = render(
        <AudioFeaturesPanel features={mockFeatures} />
      );

      // Features should have group elements with titles
      const groups = container.querySelectorAll(".group[title]");
      expect(groups.length).toBeGreaterThan(0);
    });
  });
});

describe("AudioFeaturesSummary", () => {
  describe("rendering", () => {
    it("shows BPM", () => {
      render(<AudioFeaturesSummary features={mockFeatures} />);

      expect(screen.getByText("120")).toBeInTheDocument();
      expect(screen.getByText("BPM")).toBeInTheDocument();
    });

    it("shows key signature", () => {
      const { container } = render(
        <AudioFeaturesSummary features={mockFeatures} />
      );

      // Should have KeySignatureBadge
      const keyBadge = container.querySelector(".key-signature-badge, [title*='Key']");
      expect(keyBadge || screen.queryByText(/F/)).toBeTruthy();
    });

    it("shows feature highlights", () => {
      render(<AudioFeaturesSummary features={mockFeatures} />);

      expect(screen.getByText("Energy:")).toBeInTheDocument();
      expect(screen.getByText("Danceability:")).toBeInTheDocument();
      expect(screen.getByText("Valence:")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <AudioFeaturesSummary features={mockFeatures} className="custom-summary" />
      );

      expect(container.firstChild).toHaveClass("custom-summary");
    });
  });

  describe("null handling", () => {
    it("hides BPM when null", () => {
      render(<AudioFeaturesSummary features={nullFeatures} />);

      expect(screen.queryByText("BPM")).not.toBeInTheDocument();
    });

    it("hides key when null", () => {
      render(<AudioFeaturesSummary features={nullFeatures} />);

      // No key badge should be shown
      expect(screen.queryByText(/major|minor/i)).not.toBeInTheDocument();
    });

    it("filters out null feature highlights", () => {
      render(<AudioFeaturesSummary features={partialFeatures} />);

      // Energy (0.5) and Valence (0.3) should show, Danceability is null
      expect(screen.getByText("Energy:")).toBeInTheDocument();
      expect(screen.getByText("Valence:")).toBeInTheDocument();
      expect(screen.queryByText("Danceability:")).not.toBeInTheDocument();
    });
  });
});

describe("SingleFeature", () => {
  describe("rendering", () => {
    it("shows label", () => {
      render(<SingleFeature label="Energy" value={0.8} />);

      expect(screen.getByText("Energy")).toBeInTheDocument();
    });

    it("shows percentage value", () => {
      render(<SingleFeature label="Energy" value={0.8} />);

      expect(screen.getByText("80%")).toBeInTheDocument();
    });

    it("shows progress bar by default", () => {
      const { container } = render(
        <SingleFeature label="Energy" value={0.8} />
      );

      const bar = container.querySelector(".h-1");
      expect(bar).toBeInTheDocument();
    });

    it("hides progress bar when showBar is false", () => {
      const { container } = render(
        <SingleFeature label="Energy" value={0.8} showBar={false} />
      );

      const bar = container.querySelector(".h-1");
      expect(bar).not.toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <SingleFeature label="Energy" value={0.8} className="custom-feature" />
      );

      expect(container.firstChild).toHaveClass("custom-feature");
    });
  });

  describe("null value handling", () => {
    it("shows dashes for null value", () => {
      render(<SingleFeature label="Energy" value={null} />);

      expect(screen.getByText("--")).toBeInTheDocument();
    });

    it("shows 0% width bar for null value", () => {
      const { container } = render(
        <SingleFeature label="Energy" value={null} />
      );

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ width: "0%" });
    });
  });

  describe("color intensity", () => {
    it("uses cool color for low values (<=33%)", () => {
      const { container } = render(
        <SingleFeature label="Feature" value={0.2} />
      );

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ backgroundColor: "var(--accent-cool)" });
    });

    it("uses warm color for medium values (34-66%)", () => {
      const { container } = render(
        <SingleFeature label="Feature" value={0.5} />
      );

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ backgroundColor: "var(--accent-warm)" });
    });

    it("uses needle color for high values (>66%)", () => {
      const { container } = render(
        <SingleFeature label="Feature" value={0.8} />
      );

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ backgroundColor: "var(--accent-needle)" });
    });
  });

  describe("tooltip", () => {
    it("applies tooltip via title attribute", () => {
      const { container } = render(
        <SingleFeature
          label="Energy"
          value={0.8}
          tooltip="How intense the track feels"
        />
      );

      expect(container.firstChild).toHaveAttribute(
        "title",
        "How intense the track feels"
      );
    });
  });

  describe("rounding", () => {
    it("rounds percentage values", () => {
      render(<SingleFeature label="Feature" value={0.777} />);

      expect(screen.getByText("78%")).toBeInTheDocument();
    });
  });
});
