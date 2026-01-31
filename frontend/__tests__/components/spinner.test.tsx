import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Spinner, Loading, WaveformLoader, EqualizerLoader, Skeleton } from "../../src/components/ui/spinner";

describe("Spinner", () => {
  it("renders the spinner", () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild;
    expect(spinner).toBeInTheDocument();
  });

  it("renders with default size (md)", () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild;
    expect(spinner).toHaveClass("h-8", "w-8");
  });

  it("renders with small size", () => {
    const { container } = render(<Spinner size="sm" />);
    const spinner = container.firstChild;
    expect(spinner).toHaveClass("h-4", "w-4");
  });

  it("renders with large size", () => {
    const { container } = render(<Spinner size="lg" />);
    const spinner = container.firstChild;
    expect(spinner).toHaveClass("h-12", "w-12");
  });

  it("applies custom className", () => {
    const { container } = render(<Spinner className="custom-spinner" />);
    const spinner = container.firstChild;
    expect(spinner).toHaveClass("custom-spinner");
  });

  it("is animated", () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild;
    expect(spinner).toHaveClass("animate-spin");
  });

  it("has rounded full style", () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild;
    expect(spinner).toHaveClass("rounded-full");
  });
});

describe("Loading", () => {
  it("renders with text", () => {
    const { getByText } = render(<Loading />);
    expect(getByText("Loading...")).toBeInTheDocument();
  });

  it("renders with custom text", () => {
    const { getByText } = render(<Loading text="Please wait..." />);
    expect(getByText("Please wait...")).toBeInTheDocument();
  });

  it("renders without text when empty string", () => {
    const { queryByText } = render(<Loading text="" />);
    expect(queryByText("Loading...")).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<Loading className="custom-loading" />);
    expect(container.firstChild).toHaveClass("custom-loading");
  });

  it("centers content", () => {
    const { container } = render(<Loading />);
    expect(container.firstChild).toHaveClass("flex", "items-center", "justify-center");
  });

  it("renders waveform variant by default", () => {
    const { container } = render(<Loading />);
    expect(container.querySelector(".waveform-bar")).toBeInTheDocument();
  });

  it("renders spinner variant", () => {
    const { container } = render(<Loading variant="spinner" />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders equalizer variant", () => {
    const { container } = render(<Loading variant="equalizer" />);
    expect(container.querySelector(".equalizer")).toBeInTheDocument();
  });
});

describe("WaveformLoader", () => {
  it("renders waveform bars", () => {
    const { container } = render(<WaveformLoader />);
    const bars = container.querySelectorAll(".waveform-bar");
    expect(bars.length).toBe(5);
  });

  it("renders custom number of bars", () => {
    const { container } = render(<WaveformLoader bars={3} />);
    const bars = container.querySelectorAll(".waveform-bar");
    expect(bars.length).toBe(3);
  });

  it("applies custom className", () => {
    const { container } = render(<WaveformLoader className="custom-waveform" />);
    expect(container.firstChild).toHaveClass("custom-waveform");
  });
});

describe("EqualizerLoader", () => {
  it("renders equalizer bars", () => {
    const { container } = render(<EqualizerLoader />);
    const bars = container.querySelectorAll(".equalizer-bar");
    expect(bars.length).toBe(5);
  });

  it("has equalizer class", () => {
    const { container } = render(<EqualizerLoader />);
    expect(container.firstChild).toHaveClass("equalizer");
  });

  it("applies custom className", () => {
    const { container } = render(<EqualizerLoader className="custom-equalizer" />);
    expect(container.firstChild).toHaveClass("custom-equalizer");
  });
});

describe("Skeleton", () => {
  it("renders with text variant by default", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass("h-4", "rounded");
  });

  it("renders with circular variant", () => {
    const { container } = render(<Skeleton variant="circular" />);
    expect(container.firstChild).toHaveClass("rounded-full");
  });

  it("renders with rectangular variant", () => {
    const { container } = render(<Skeleton variant="rectangular" />);
    expect(container.firstChild).toHaveClass("rounded-xl");
  });

  it("has shimmer animation", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass("shimmer");
  });

  it("applies custom className", () => {
    const { container } = render(<Skeleton className="custom-skeleton" />);
    expect(container.firstChild).toHaveClass("custom-skeleton");
  });

  it("accepts width and height props", () => {
    const { container } = render(<Skeleton width={100} height={50} />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.style.width).toBe("100px");
    expect(skeleton.style.height).toBe("50px");
  });
});
