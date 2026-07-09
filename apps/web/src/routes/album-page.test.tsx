import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import {
  makeAlbum,
  makeConfig,
  makeDownloadSubmit,
} from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function serveAlbum() {
  server.use(
    http.get("*/api/v1/albums/:id", ({ params }) =>
      HttpResponse.json(makeAlbum({ id: String(params.id) })),
    ),
  );
}

describe("Album page", () => {
  it("renders the album's tracks", async () => {
    serveAlbum();
    renderApp("/albums/album-1");

    expect(await screen.findByText("Get Lucky")).toBeInTheDocument();
    expect(screen.getByText("Instant Crush")).toBeInTheDocument();
  });

  it("Enqueue all posts the album query and links to the queue", async () => {
    serveAlbum();
    let posted: { query?: string } | null = null;
    server.use(
      http.post("*/api/v1/downloads", async ({ request }) => {
        posted = (await request.json()) as { query?: string };
        return HttpResponse.json(makeDownloadSubmit(), { status: 201 });
      }),
    );
    renderApp("/albums/album-1");

    const button = await screen.findByRole("button", { name: "Enqueue all" });
    await userEvent.click(button);

    await waitFor(() => expect(posted).not.toBeNull());
    expect(posted!.query).toBe("album-1");
    expect(
      await screen.findByRole("link", { name: /view downloads/i }),
    ).toBeInTheDocument();
  });

  it("hides Enqueue all when downloads are disabled", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json(makeConfig({ mode: "hosted" })),
      ),
    );
    serveAlbum();
    renderApp("/albums/album-1");

    // The track list still renders in a downloads-off mode…
    expect(await screen.findByText("Get Lucky")).toBeInTheDocument();
    // …but the batch-enqueue action is gated away (CONTRACT G).
    expect(
      screen.queryByRole("button", { name: "Enqueue all" }),
    ).not.toBeInTheDocument();
  });
});
