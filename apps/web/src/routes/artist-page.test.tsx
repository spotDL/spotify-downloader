import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { AlbumOut } from "../api/generated/types.gen";
import { server } from "../test/msw/server";
import { makeAlbum, makeArtist } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function serveArtist() {
  server.use(
    http.get("*/api/v1/artists/:id", ({ params }) =>
      HttpResponse.json(makeArtist({ id: String(params.id) })),
    ),
  );
}

// A two-entry discography: a full-length album and a single (metadata-only, each
// carrying a source ref for resolve-on-open).
const DISCOGRAPHY: AlbumOut[] = [
  makeAlbum({
    id: "al-ram",
    name: "Random Access Memories",
    album_type: "album",
    provider: "spotify",
    provider_id: "sp-ram",
    tracks: [],
  }),
  makeAlbum({
    id: "al-ic",
    name: "Instant Crush",
    album_type: "single",
    provider: "spotify",
    provider_id: "sp-ic",
    tracks: [],
  }),
];

function serveArtistWithDiscography() {
  server.use(
    http.get("*/api/v1/artists/:id", ({ params }) =>
      HttpResponse.json(makeArtist({ id: String(params.id), albums: DISCOGRAPHY })),
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

  it("shows one merged Sources panel listing each provider once with its reach", async () => {
    serveArtist();
    renderApp("/artists/artist-1");

    // Default sources handler serves Spotify + Deezer follower snapshots, folded
    // into a single panel — the old reach-vs-provenance duplication is gone.
    // Await a data-derived value so we're past the loading card, which also
    // carries the "Sources" title.
    expect(await screen.findByText("34.2M")).toBeInTheDocument();
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.queryByText("Reach across platforms")).not.toBeInTheDocument();
    expect(screen.queryByText("Metadata sources")).not.toBeInTheDocument();

    // Each provider's follower snapshot shows once, in mono, beside its ★ score.
    expect(screen.getByText("4.5M")).toBeInTheDocument();
    // Deezer is listed exactly once now (no duplicate card).
    expect(screen.getAllByText("Deezer")).toHaveLength(1);
  });

  it("renders the discography grid with album-type filter tabs that narrow it", async () => {
    serveArtistWithDiscography();
    const user = userEvent.setup();
    renderApp("/artists/artist-1");

    // Both releases show under the default "All" tab.
    expect(await screen.findByText("Random Access Memories")).toBeInTheDocument();
    expect(screen.getByText("Instant Crush")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "All" })).toBeInTheDocument();

    // Filtering to Singles drops the full-length album.
    await user.click(screen.getByRole("tab", { name: "Singles" }));
    expect(screen.queryByText("Random Access Memories")).not.toBeInTheDocument();
    expect(screen.getByText("Instant Crush")).toBeInTheDocument();
  });

  it("resolves a discography album on open (resolve-on-open via its source ref)", async () => {
    serveArtistWithDiscography();
    // A metadata-only album resolves its provider ref into a canonical album.
    server.use(
      http.post("*/api/v1/resolve", () =>
        HttpResponse.json({
          entity: {
            type: "album",
            album: makeAlbum({ id: "album-1", name: "Random Access Memories" }),
          },
          degraded_sources: [],
        }),
      ),
      http.get("*/api/v1/albums/:id", ({ params }) =>
        HttpResponse.json(makeAlbum({ id: String(params.id) })),
      ),
    );
    const user = userEvent.setup();
    renderApp("/artists/artist-1");

    // The cover button is labelled by the album name; clicking it resolves-then-opens.
    await user.click(await screen.findByRole("button", { name: "Random Access Memories" }));
    // We land on /albums/album-1 → the album page renders the resolved album's <h1>.
    expect(
      await screen.findByRole("heading", { level: 1, name: "Random Access Memories" }),
    ).toBeInTheDocument();
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
