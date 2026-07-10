import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeArtist } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function serveArtist() {
  server.use(
    http.get("*/api/v1/artists/:id", ({ params }) =>
      HttpResponse.json(makeArtist({ id: String(params.id) })),
    ),
  );
}

describe("Artist page", () => {
  it("renders the artist's top tracks", async () => {
    serveArtist();
    renderApp("/artists/artist-1");

    expect(await screen.findByRole("heading", { name: "Daft Punk" })).toBeInTheDocument();
    expect(screen.getByText("Get Lucky")).toBeInTheDocument();
  });

  it("renders followers, popularity, and a truncated genre chip row", async () => {
    serveArtist();
    renderApp("/artists/artist-1");

    // followers 33_901_227 → compacted; popularity is a 0–100 stat chip.
    expect(await screen.findByText("33.9M")).toBeInTheDocument();
    expect(screen.getByText("followers")).toBeInTheDocument();
    expect(screen.getByText("88")).toBeInTheDocument();
    // 6 fixture genres → first 5 chips + a "+1" overflow chip.
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("omits the About card when the artist has no bio", async () => {
    serveArtist();
    renderApp("/artists/artist-1");
    expect(await screen.findByRole("heading", { name: "Daft Punk" })).toBeInTheDocument();
    expect(screen.queryByText("About")).not.toBeInTheDocument();
  });

  it("renders an About card when the artist has a bio", async () => {
    server.use(
      http.get("*/api/v1/artists/:id", ({ params }) =>
        HttpResponse.json(
          makeArtist({ id: String(params.id), bio: "A French electronic duo." }),
        ),
      ),
    );
    renderApp("/artists/artist-1");
    expect(await screen.findByText("About")).toBeInTheDocument();
    expect(screen.getByText("A French electronic duo.")).toBeInTheDocument();
  });

  it("shows 'Reach across platforms' with two providers plus a metadata-sources panel", async () => {
    serveArtist();
    renderApp("/artists/artist-1");

    // Default sources handler serves Spotify + Deezer follower snapshots.
    expect(
      await screen.findByText("Reach across platforms"),
    ).toBeInTheDocument();
    // Deezer's fan count shows only in the reach card; the honest label sits beside it.
    expect(screen.getByText("4.5M")).toBeInTheDocument();
    expect(screen.getByText(/not licensed play counts/i)).toBeInTheDocument();
    // The provenance panel lists both providers by name (Deezer appears in both
    // the reach card and the sources panel).
    expect(screen.getByText("Metadata sources")).toBeInTheDocument();
    expect(screen.getAllByText("Deezer").length).toBeGreaterThanOrEqual(2);
  });

  it("never offers Enqueue all (an artist is not a downloadable batch)", async () => {
    // Even in a downloads-ON mode (selfhost is the fixture default), the artist
    // page has no batch enqueue — per Plan 8's `unsupported_entity` rule.
    serveArtist();
    renderApp("/artists/artist-1");

    expect(await screen.findByText("Get Lucky")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Enqueue all" }),
    ).not.toBeInTheDocument();
  });
});
