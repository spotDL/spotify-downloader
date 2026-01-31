import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "../../src/components/ui/badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Badge Text</Badge>);
    expect(screen.getByText("Badge Text")).toBeInTheDocument();
  });

  it("renders with default variant", () => {
    render(<Badge>Default</Badge>);
    const badge = screen.getByText("Default");
    expect(badge).toHaveClass("bg-gray-700");
  });

  it("renders with success variant", () => {
    render(<Badge variant="success">Success</Badge>);
    const badge = screen.getByText("Success");
    expect(badge).toHaveClass("bg-green-900/50", "text-green-400");
  });

  it("renders with warning variant", () => {
    render(<Badge variant="warning">Warning</Badge>);
    const badge = screen.getByText("Warning");
    expect(badge).toHaveClass("bg-yellow-900/50", "text-yellow-400");
  });

  it("renders with error variant", () => {
    render(<Badge variant="error">Error</Badge>);
    const badge = screen.getByText("Error");
    expect(badge).toHaveClass("bg-red-900/50", "text-red-400");
  });

  it("renders with info variant", () => {
    render(<Badge variant="info">Info</Badge>);
    const badge = screen.getByText("Info");
    expect(badge).toHaveClass("bg-blue-900/50", "text-blue-400");
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

  it("has rounded-full styling", () => {
    render(<Badge>Rounded</Badge>);
    const badge = screen.getByText("Rounded");
    expect(badge).toHaveClass("rounded-full");
  });

  it("has proper text sizing", () => {
    render(<Badge>Sized</Badge>);
    const badge = screen.getByText("Sized");
    expect(badge).toHaveClass("text-xs", "font-medium");
  });
});
