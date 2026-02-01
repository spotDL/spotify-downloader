import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  MatchScoreGauge,
  MatchScoreBar,
  ScoreBadge,
} from "../../src/components/ui/match-gauge";

describe("MatchScoreGauge", () => {
  describe("rendering", () => {
    it("renders with score label by default", () => {
      render(<MatchScoreGauge score={85} />);

      expect(screen.getByText("85")).toBeInTheDocument();
    });

    it("rounds decimal scores", () => {
      render(<MatchScoreGauge score={85.7} />);

      expect(screen.getByText("86")).toBeInTheDocument();
    });

    it("hides label when showLabel is false", () => {
      render(<MatchScoreGauge score={85} showLabel={false} />);

      expect(screen.queryByText("85")).not.toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <MatchScoreGauge score={85} className="custom-gauge" />
      );

      expect(container.firstChild).toHaveClass("custom-gauge");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      const { container } = render(<MatchScoreGauge score={85} size="sm" />);

      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("width", "48");
      expect(svg).toHaveAttribute("height", "48");
    });

    it("renders medium size (default)", () => {
      const { container } = render(<MatchScoreGauge score={85} />);

      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("width", "64");
      expect(svg).toHaveAttribute("height", "64");
    });

    it("renders large size", () => {
      const { container } = render(<MatchScoreGauge score={85} size="lg" />);

      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("width", "96");
      expect(svg).toHaveAttribute("height", "96");
    });
  });

  describe("color thresholds", () => {
    it("uses green color for high scores (90+)", () => {
      const { container } = render(<MatchScoreGauge score={95} />);

      expect(container.firstChild).toHaveAttribute("data-score", "high");
      // Check that the color CSS variable is set
      const style = (container.firstChild as HTMLElement).style;
      expect(style.getPropertyValue("--score-color")).toBe("var(--accent-safe)");
    });

    it("uses yellow/warm color for medium scores (70-89)", () => {
      const { container } = render(<MatchScoreGauge score={75} />);

      expect(container.firstChild).toHaveAttribute("data-score", "medium");
      const style = (container.firstChild as HTMLElement).style;
      expect(style.getPropertyValue("--score-color")).toBe("var(--accent-warm)");
    });

    it("uses red/peak color for low scores (<70)", () => {
      const { container } = render(<MatchScoreGauge score={50} />);

      expect(container.firstChild).toHaveAttribute("data-score", "low");
      const style = (container.firstChild as HTMLElement).style;
      expect(style.getPropertyValue("--score-color")).toBe("var(--accent-peak)");
    });

    it("treats 90 as high threshold boundary", () => {
      const { container } = render(<MatchScoreGauge score={90} />);

      expect(container.firstChild).toHaveAttribute("data-score", "high");
    });

    it("treats 70 as medium threshold boundary", () => {
      const { container } = render(<MatchScoreGauge score={70} />);

      expect(container.firstChild).toHaveAttribute("data-score", "medium");
    });

    it("treats 69 as low", () => {
      const { container } = render(<MatchScoreGauge score={69} />);

      expect(container.firstChild).toHaveAttribute("data-score", "low");
    });
  });

  describe("score normalization", () => {
    it("clamps scores above 100 to 100", () => {
      render(<MatchScoreGauge score={150} />);

      expect(screen.getByText("100")).toBeInTheDocument();
    });

    it("clamps negative scores to 0", () => {
      render(<MatchScoreGauge score={-10} />);

      expect(screen.getByText("0")).toBeInTheDocument();
    });

    it("handles zero score", () => {
      render(<MatchScoreGauge score={0} />);

      expect(screen.getByText("0")).toBeInTheDocument();
    });

    it("handles score of exactly 100", () => {
      render(<MatchScoreGauge score={100} />);

      expect(screen.getByText("100")).toBeInTheDocument();
    });
  });

  describe("animation", () => {
    it("applies animation class when animated is true (default)", () => {
      const { container } = render(<MatchScoreGauge score={85} />);

      const scoreCircle = container.querySelectorAll("circle")[1];
      expect(scoreCircle).toHaveClass("animate-[scoreGaugeFill_1s_ease-out_forwards]");
    });

    it("does not apply animation class when animated is false", () => {
      const { container } = render(<MatchScoreGauge score={85} animated={false} />);

      const scoreCircle = container.querySelectorAll("circle")[1];
      expect(scoreCircle).not.toHaveClass("animate-[scoreGaugeFill_1s_ease-out_forwards]");
    });
  });

  describe("SVG structure", () => {
    it("renders two circles (background and score arc)", () => {
      const { container } = render(<MatchScoreGauge score={85} />);

      const circles = container.querySelectorAll("circle");
      expect(circles.length).toBe(2);
    });

    it("has correct viewBox", () => {
      const { container } = render(<MatchScoreGauge score={85} size="md" />);

      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("viewBox", "0 0 64 64");
    });
  });
});

describe("MatchScoreBar", () => {
  describe("rendering", () => {
    it("renders progress bar", () => {
      const { container } = render(<MatchScoreBar score={75} />);

      const progressBar = container.querySelector(".h-2");
      expect(progressBar).toBeInTheDocument();
    });

    it("shows percentage by default", () => {
      render(<MatchScoreBar score={75} />);

      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    it("hides percentage when showPercentage is false", () => {
      render(<MatchScoreBar score={75} showPercentage={false} />);

      expect(screen.queryByText("75%")).not.toBeInTheDocument();
    });

    it("shows label when showLabel is true", () => {
      render(<MatchScoreBar score={75} showLabel />);

      expect(screen.getByText("Match Score")).toBeInTheDocument();
    });

    it("hides label by default", () => {
      render(<MatchScoreBar score={75} />);

      expect(screen.queryByText("Match Score")).not.toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <MatchScoreBar score={75} className="custom-bar" />
      );

      expect(container.firstChild).toHaveClass("custom-bar");
    });
  });

  describe("progress fill", () => {
    it("fills bar according to score percentage", () => {
      const { container } = render(<MatchScoreBar score={50} />);

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ width: "50%" });
    });

    it("handles 0% fill", () => {
      const { container } = render(<MatchScoreBar score={0} />);

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ width: "0%" });
    });

    it("handles 100% fill", () => {
      const { container } = render(<MatchScoreBar score={100} />);

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ width: "100%" });
    });
  });

  describe("color thresholds", () => {
    it("uses appropriate color for high scores", () => {
      const { container } = render(<MatchScoreBar score={95} />);

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ backgroundColor: "var(--accent-safe)" });
    });

    it("uses appropriate color for medium scores", () => {
      const { container } = render(<MatchScoreBar score={75} />);

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ backgroundColor: "var(--accent-warm)" });
    });

    it("uses appropriate color for low scores", () => {
      const { container } = render(<MatchScoreBar score={50} />);

      const fill = container.querySelector(".h-full.rounded-full");
      expect(fill).toHaveStyle({ backgroundColor: "var(--accent-peak)" });
    });
  });

  describe("score normalization", () => {
    it("clamps scores above 100", () => {
      render(<MatchScoreBar score={150} />);

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("clamps negative scores to 0", () => {
      render(<MatchScoreBar score={-10} />);

      expect(screen.getByText("0%")).toBeInTheDocument();
    });
  });
});

describe("ScoreBadge", () => {
  describe("rendering", () => {
    it("renders score with percentage", () => {
      render(<ScoreBadge score={85} />);

      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("rounds decimal scores", () => {
      render(<ScoreBadge score={85.4} />);

      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <ScoreBadge score={85} className="custom-badge" />
      );

      expect(container.firstChild).toHaveClass("custom-badge");
    });
  });

  describe("color classes", () => {
    it("applies high score background class", () => {
      const { container } = render(<ScoreBadge score={95} />);

      expect(container.firstChild).toHaveClass("bg-[var(--accent-safe)]/10");
    });

    it("applies medium score background class", () => {
      const { container } = render(<ScoreBadge score={75} />);

      expect(container.firstChild).toHaveClass("bg-[var(--accent-warm)]/10");
    });

    it("applies low score background class", () => {
      const { container } = render(<ScoreBadge score={50} />);

      expect(container.firstChild).toHaveClass("bg-[var(--accent-peak)]/10");
    });
  });

  describe("text color", () => {
    it("uses matching text color for high scores", () => {
      const { container } = render(<ScoreBadge score={95} />);

      const badge = container.firstChild as HTMLElement;
      expect(badge.style.color).toBe("var(--accent-safe)");
    });

    it("uses matching text color for medium scores", () => {
      const { container } = render(<ScoreBadge score={75} />);

      const badge = container.firstChild as HTMLElement;
      expect(badge.style.color).toBe("var(--accent-warm)");
    });

    it("uses matching text color for low scores", () => {
      const { container } = render(<ScoreBadge score={50} />);

      const badge = container.firstChild as HTMLElement;
      expect(badge.style.color).toBe("var(--accent-peak)");
    });
  });

  describe("score normalization", () => {
    it("clamps scores above 100", () => {
      render(<ScoreBadge score={150} />);

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("clamps negative scores to 0", () => {
      render(<ScoreBadge score={-10} />);

      expect(screen.getByText("0%")).toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("has pill/badge shape", () => {
      const { container } = render(<ScoreBadge score={85} />);

      expect(container.firstChild).toHaveClass("rounded-full");
    });

    it("uses monospace font", () => {
      const { container } = render(<ScoreBadge score={85} />);

      expect(container.firstChild).toHaveClass("font-mono");
    });
  });
});
