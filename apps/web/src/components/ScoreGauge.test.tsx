import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScoreGauge } from "./ScoreGauge";

describe("ScoreGauge", () => {
  it("exposes the score as a meter with aria-valuenow on the 0–1 scale", () => {
    render(<ScoreGauge score={0.94} netScore={3} />);
    const meter = screen.getByRole("meter", { name: "Match score" });
    expect(meter).toHaveAttribute("aria-valuenow", "0.94");
    expect(meter).toHaveAttribute("aria-valuemin", "0");
    expect(meter).toHaveAttribute("aria-valuemax", "1");
    expect(meter).toHaveAttribute("aria-valuetext", "94%");
  });

  it("renders the net_score as a signed secondary figure", () => {
    render(<ScoreGauge score={0.5} netScore={-2} />);
    expect(screen.getByText("-2")).toBeInTheDocument();
    render(<ScoreGauge score={0.5} netScore={5} />);
    expect(screen.getByText("+5")).toBeInTheDocument();
  });

  it("clamps out-of-range scores", () => {
    render(<ScoreGauge score={1.4} />);
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "1");
  });
});
