import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { VuGauge } from "./VuGauge";

// Ported from the former ScoreGauge tests — the 0–1 scale + clamp is the
// score-scale regression guard (the wire delivers 0–100; callers pass score/100).
describe("VuGauge", () => {
  it("exposes the score as a meter with aria-valuenow on the 0–1 scale", () => {
    render(<VuGauge score={0.94} />);
    const meter = screen.getByRole("meter", { name: "Match score" });
    expect(meter).toHaveAttribute("aria-valuenow", "0.94");
    expect(meter).toHaveAttribute("aria-valuemin", "0");
    expect(meter).toHaveAttribute("aria-valuemax", "1");
    expect(meter).toHaveAttribute("aria-valuetext", "94%");
  });

  it("renders the rounded percentage label", () => {
    render(<VuGauge score={0.87} />);
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("clamps out-of-range scores", () => {
    render(<VuGauge score={1.4} />);
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "1");
  });
});
