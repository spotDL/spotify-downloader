import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge, PlatformBadge } from "../../src/components/ui/badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Badge Text</Badge>);
    expect(screen.getByText("Badge Text")).toBeInTheDocument();
  });

  it("renders with default variant", () => {
    render(<Badge>Default</Badge>);
    const badge = screen.getByText("Default");
    expect(badge).toHaveClass("bg-zinc-800");
  });

  it("renders with success variant", () => {
    render(<Badge variant="success">Success</Badge>);
    const badge = screen.getByText("Success");
    expect(badge).toHaveClass("bg-emerald-950/50", "text-emerald-400");
  });

  it("renders with warning variant", () => {
    render(<Badge variant="warning">Warning</Badge>);
    const badge = screen.getByText("Warning");
    expect(badge).toHaveClass("bg-amber-950/50", "text-amber-400");
  });

  it("renders with error variant", () => {
    render(<Badge variant="error">Error</Badge>);
    const badge = screen.getByText("Error");
    expect(badge).toHaveClass("bg-red-950/50", "text-red-400");
  });

  it("renders with info variant", () => {
    render(<Badge variant="info">Info</Badge>);
    const badge = screen.getByText("Info");
    expect(badge).toHaveClass("bg-sky-950/50", "text-sky-400");
  });

  it("renders with premium variant", () => {
    render(<Badge variant="premium">Premium</Badge>);
    const badge = screen.getByText("Premium");
    expect(badge).toHaveClass("bg-gradient-to-r");
  });

  it("applies custom className", () => {
    render(<Badge className="custom-badge">Custom</Badge>);
    const badge = screen.getByText("Custom");
    expect(badge).toHaveClass("custom-badge");
  });

  it("passes through other props", () => {
    render(<Badge data-testid="test-badge">Test</Badge>);
    expect(screen.getByTestId("test-badge")).toBeInTheDocument();
  });

  it("has rounded-lg styling", () => {
    render(<Badge>Rounded</Badge>);
    const badge = screen.getByText("Rounded");
    expect(badge).toHaveClass("rounded-lg");
  });

  it("has proper text sizing for md size", () => {
    render(<Badge>Sized</Badge>);
    const badge = screen.getByText("Sized");
    expect(badge).toHaveClass("text-xs", "font-medium");
  });

  it("has proper text sizing for sm size", () => {
    render(<Badge size="sm">Small</Badge>);
    const badge = screen.getByText("Small");
    expect(badge).toHaveClass("text-[10px]");
  });

  it("renders pulse indicator when pulse prop is true", () => {
    const { container } = render(<Badge pulse variant="success">Pulsing</Badge>);
    expect(container.querySelector(".animate-ping")).toBeInTheDocument();
  });
});

describe("PlatformBadge", () => {
  it("renders spotify badge", () => {
    render(<PlatformBadge platform="spotify" />);
    expect(screen.getByText("Spotify")).toBeInTheDocument();
  });

  it("renders apple music badge", () => {
    render(<PlatformBadge platform="apple_music" />);
    expect(screen.getByText("Apple Music")).toBeInTheDocument();
  });

  it("renders youtube music badge", () => {
    render(<PlatformBadge platform="youtube_music" />);
    expect(screen.getByText("YouTube Music")).toBeInTheDocument();
  });

  it("renders with correct styling", () => {
    render(<PlatformBadge platform="spotify" data-testid="spotify-badge" />);
    const badge = screen.getByTestId("spotify-badge");
    expect(badge).toHaveClass("rounded-lg", "font-semibold");
  });
});
