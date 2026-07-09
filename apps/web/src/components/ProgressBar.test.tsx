import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgressBar } from "./ProgressBar";

describe("ProgressBar", () => {
  it("exposes a determinate progressbar with aria-valuenow and the phase label", () => {
    render(<ProgressBar percent={0.42} phase="Downloading" />);
    const bar = screen.getByRole("progressbar", { name: "Downloading" });
    expect(bar).toHaveAttribute("aria-valuenow", "42");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
    expect(screen.getByText("Downloading")).toBeInTheDocument();
  });

  it("omits aria-valuenow when indeterminate (percent null)", () => {
    render(<ProgressBar percent={null} phase="Starting" />);
    const bar = screen.getByRole("progressbar", { name: "Starting" });
    expect(bar).not.toHaveAttribute("aria-valuenow");
  });

  it("clamps out-of-range percentages", () => {
    render(<ProgressBar percent={1.5} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });
});
