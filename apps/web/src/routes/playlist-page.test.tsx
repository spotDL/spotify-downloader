import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import {
  makeConfig,
  makeDownloadSubmit,
  makePlaylist,
} from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function servePlaylist() {
  server.use(
    http.get("*/api/v1/playlists/:id", ({ params }) =>
      HttpResponse.json(makePlaylist({ id: String(params.id) })),
    ),
  );
}

describe("Playlist page", () => {
  it("renders the playlist's tracks and owner", async () => {
    servePlaylist();
    renderApp("/playlists/playlist-1");

    expect(await screen.findByText("Summer Mix")).toBeInTheDocument();
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByText("One More Time")).toBeInTheDocument();
  });

  it("Enqueue all posts the playlist query", async () => {
    servePlaylist();
    let posted: { query?: string } | null = null;
    server.use(
      http.post("*/api/v1/downloads", async ({ request }) => {
        posted = (await request.json()) as { query?: string };
        return HttpResponse.json(makeDownloadSubmit(), { status: 201 });
      }),
    );
    renderApp("/playlists/playlist-1");

    await userEvent.click(
      await screen.findByRole("button", { name: "Enqueue all" }),
    );

    await waitFor(() => expect(posted).not.toBeNull());
    expect(posted!.query).toBe("playlist-1");
  });

  it("hides Enqueue all when downloads are disabled", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json(makeConfig({ mode: "hosted" })),
      ),
    );
    servePlaylist();
    renderApp("/playlists/playlist-1");

    expect(await screen.findByText("Summer Mix")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Enqueue all" }),
    ).not.toBeInTheDocument();
  });
});
