import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ResolveResponse } from "../api/generated/types.gen";
import { server } from "../test/msw/server";
import { makeTrack } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function serveResolve(handler: Parameters<typeof http.post>[1]) {
  server.use(http.post("*/api/v1/resolve", handler));
}

async function submitLink(url: string) {
  const user = userEvent.setup();
  const input = await screen.findByLabelText("Paste a link");
  await user.type(input, url);
  await user.click(screen.getByRole("button", { name: "Open" }));
}

describe("home resolve flow", () => {
  it("navigates to the resolved track page on a clean resolve", async () => {
    const body: ResolveResponse = {
      entity: { type: "track", track: makeTrack({ id: "track-42" }) },
      degraded_sources: [],
    };
    serveResolve(() => HttpResponse.json(body));

    renderApp("/");
    await submitLink("https://open.spotify.com/track/track-42");

    // The default tracks handler serves makeTrack (name "Get Lucky") for the id;
    // seeing its <h1> proves we navigated to /tracks/track-42.
    expect(
      await screen.findByRole("heading", { level: 1, name: "Get Lucky" }),
    ).toBeInTheDocument();
  });

  it("toasts on an unsupported_url error", async () => {
    serveResolve(() =>
      HttpResponse.json(
        { code: "unsupported_url", message: "nope", detail: null },
        { status: 400 },
      ),
    );

    renderApp("/");
    await submitLink("not-a-real-link");

    expect(
      await screen.findByText("That link or query isn't supported."),
    ).toBeInTheDocument();
  });

  it("shows the degraded-sources banner instead of navigating when sources degraded", async () => {
    const body: ResolveResponse = {
      entity: { type: "track", track: makeTrack({ id: "track-9" }) },
      degraded_sources: ["musicbrainz"],
    };
    serveResolve(() => HttpResponse.json(body));

    renderApp("/");
    await submitLink("https://open.spotify.com/track/track-9");

    expect(
      await screen.findByText(/some sources were unavailable/i),
    ).toBeInTheDocument();
    // We stayed on the home page (no auto-navigation on partial data).
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /continue to/i }),
      ).toBeInTheDocument(),
    );
  });
});
