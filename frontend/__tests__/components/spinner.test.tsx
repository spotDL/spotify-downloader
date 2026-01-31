import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Spinner, Loading } from "../../src/components/ui/spinner";

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
  it("renders spinner with text", () => {
    const { container, getByText } = render(<Loading />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    expect(getByText("Loading...")).toBeInTheDocument();
  });

  it("renders with custom text", () => {
    const { getByText } = render(<Loading text="Please wait..." />);
    expect(getByText("Please wait...")).toBeInTheDocument();
  });

  it("renders without text when empty string", () => {
    const { container, queryByText } = render(<Loading text="" />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    expect(queryByText("Loading...")).not.toBeInTheDocument();
  });

  it("passes size to spinner", () => {
    const { container } = render(<Loading size="lg" />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toHaveClass("h-12", "w-12");
  });

  it("applies custom className", () => {
    const { container } = render(<Loading className="custom-loading" />);
    expect(container.firstChild).toHaveClass("custom-loading");
  });

  it("centers content", () => {
    const { container } = render(<Loading />);
    expect(container.firstChild).toHaveClass("flex", "items-center", "justify-center");
  });
});
