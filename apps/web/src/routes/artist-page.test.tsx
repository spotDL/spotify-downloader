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
