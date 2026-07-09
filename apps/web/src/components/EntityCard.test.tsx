import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EntityCard } from "./EntityCard";

describe("EntityCard", () => {
  it("renders title, subtitle, and a type badge, linking to the entity route", () => {
    render(
      <EntityCard
        type="album"
        id="album-1"
        name="Random Access Memories"
        subtitle="Daft Punk"
        imageUrl="https://example.com/cover.jpg"
      />,
    );
    const link = screen.getByRole("link", { name: /Random Access Memories/ });
    expect(link).toHaveAttribute("href", "/albums/album-1");
    expect(screen.getByText("Daft Punk")).toBeInTheDocument();
    expect(screen.getByText("album")).toBeInTheDocument();
    // Cover art is decorative (alt=""), so it's exposed as presentation, not img.
    expect(screen.getByRole("presentation")).toHaveAttribute(
      "src",
      "https://example.com/cover.jpg",
    );
  });

  it("routes each entity type to its own path and drops the image when absent", () => {
    render(<EntityCard type="track" id="t1" name="Get Lucky" />);
    expect(screen.getByRole("link", { name: /Get Lucky/ })).toHaveAttribute(
      "href",
      "/tracks/t1",
    );
    expect(screen.queryByRole("presentation")).not.toBeInTheDocument();
  });
});
