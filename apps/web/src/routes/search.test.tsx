import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { SearchResponse } from "../api/generated/types.gen";
import { server } from "../test/msw/server";
import { makeTrack } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function serveSearch(body: SearchResponse) {
  server.use(http.get("*/api/v1/search", () => HttpResponse.json(body)));
}

describe("search results route", () => {
  it("renders the tracks MSW returns for the query", async () => {
    serveSearch({
      results: [
        makeTrack({ id: "t1", name: "Get Lucky", artists: ["Daft Punk"] }),
        makeTrack({ id: "t2", name: "Instant Crush", artists: ["Daft Punk"] }),
      ],
      degraded_sources: [],
    });

    renderApp("/search?q=daft");

    expect(await screen.findByText("Get Lucky")).toBeInTheDocument();
    expect(screen.getByText("Instant Crush")).toBeInTheDocument();
    // Results link to the track page.
    const link = screen.getByText("Get Lucky").closest("a");
    expect(link).toHaveAttribute("href", expect.stringContaining("/tracks/t1"));
  });

  it("shows the degraded-sources banner when a source was unavailable", async () => {
    serveSearch({
      results: [makeTrack({ id: "t1", name: "Get Lucky" })],
      degraded_sources: ["deezer"],
    });

    renderApp("/search?q=daft");

    expect(
      await screen.findByText(/some sources were unavailable/i),
    ).toBeInTheDocument();
  });

  it("renders the empty state and issues no search for a blank query", async () => {
    const searchHandler = vi.fn(() =>
      HttpResponse.json<SearchResponse>({ results: [], degraded_sources: [] }),
    );
    server.use(http.get("*/api/v1/search", searchHandler));

    renderApp("/search");

    expect(await screen.findByText("Search spotDL")).toBeInTheDocument();
    // The query hook is disabled for a blank query — no request is made.
    await waitFor(() => expect(searchHandler).not.toHaveBeenCalled());
  });
});
