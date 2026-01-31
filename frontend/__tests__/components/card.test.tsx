import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../../src/components/ui/card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card Content</Card>);
    expect(screen.getByText("Card Content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<Card className="custom-class">Content</Card>);
    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("renders with default variant", () => {
    const { container } = render(<Card>Content</Card>);
    expect(container.firstChild).toHaveClass("bg-gray-800");
  });

  it("renders with bordered variant", () => {
    const { container } = render(<Card variant="bordered">Content</Card>);
    expect(container.firstChild).toHaveClass("border", "border-gray-700");
  });

  it("renders with elevated variant", () => {
    const { container } = render(<Card variant="elevated">Content</Card>);
    expect(container.firstChild).toHaveClass("shadow-lg");
  });
});

describe("CardHeader", () => {
  it("renders children", () => {
    render(<CardHeader>Header Content</CardHeader>);
    expect(screen.getByText("Header Content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<CardHeader className="header-class">Header</CardHeader>);
    expect(container.firstChild).toHaveClass("header-class");
  });
});

describe("CardTitle", () => {
  it("renders children", () => {
    render(<CardTitle>Title Content</CardTitle>);
    expect(screen.getByText("Title Content")).toBeInTheDocument();
  });

  it("renders as h3 by default", () => {
    render(<CardTitle>Title</CardTitle>);
    expect(screen.getByRole("heading", { level: 3 })).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<CardTitle className="title-class">Title</CardTitle>);
    expect(container.firstChild).toHaveClass("title-class");
  });
});

describe("CardDescription", () => {
  it("renders children", () => {
    render(<CardDescription>Description Content</CardDescription>);
    expect(screen.getByText("Description Content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<CardDescription className="desc-class">Description</CardDescription>);
    expect(container.firstChild).toHaveClass("desc-class");
  });
});

describe("CardContent", () => {
  it("renders children", () => {
    render(<CardContent>Content Here</CardContent>);
    expect(screen.getByText("Content Here")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<CardContent className="content-class">Content</CardContent>);
    expect(container.firstChild).toHaveClass("content-class");
  });
});

describe("CardFooter", () => {
  it("renders children", () => {
    render(<CardFooter>Footer Content</CardFooter>);
    expect(screen.getByText("Footer Content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<CardFooter className="footer-class">Footer</CardFooter>);
    expect(container.firstChild).toHaveClass("footer-class");
  });
});

describe("Card composition", () => {
  it("renders full card with all components", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
          <CardDescription>Test Description</CardDescription>
        </CardHeader>
        <CardContent>Test Content</CardContent>
        <CardFooter>Test Footer</CardFooter>
      </Card>
    );

    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("Test Description")).toBeInTheDocument();
    expect(screen.getByText("Test Content")).toBeInTheDocument();
    expect(screen.getByText("Test Footer")).toBeInTheDocument();
  });
});
