import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeSource, makeSources } from "../test/msw/fixtures";
import { SourcesPanel } from "./SourcesPanel";

function wrap(node: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{node}</QueryClientProvider>,
  );
}

describe("SourcesPanel", () => {
  it("merges every provider snapshot into one panel with its reach and popularity", async () => {
    // Default handler serves Spotify + Deezer artist sources with follower and
    // popularity snapshots.
    wrap(<SourcesPanel entityType="artist" id="artist-1" />);

    // One merged "Sources" panel — never a separate reach card. Await a
    // data-derived provider name so we're past the loading card (which also
    // renders the "Sources" title).
    expect(await screen.findByText("Spotify")).toBeInTheDocument();
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.queryByText("Reach across platforms")).not.toBeInTheDocument();

    // Each provider appears exactly once, with its own follower count in mono…
    expect(screen.getByText("Deezer")).toBeInTheDocument();
    expect(screen.getByText("34.2M")).toBeInTheDocument();
    expect(screen.getByText("4.5M")).toBeInTheDocument();
    // …and its 0–100 popularity as a ★ chip.
    expect(screen.getByText("★ 88")).toBeInTheDocument();
    expect(screen.getByText("★ 90")).toBeInTheDocument();

    // A public per-provider link (emerald voice) is offered when we can build one.
    expect(
      screen.getByRole("link", { name: "Open on Spotify" }),
    ).toBeInTheDocument();
  });

  it("omits the panel when there are no sources", async () => {
    server.use(
      http.get("*/api/v1/tracks/:id/sources", ({ params }) =>
        HttpResponse.json(
          makeSources({ entity_type: "track", entity_id: String(params.id), sources: [] }),
        ),
      ),
    );
    wrap(<SourcesPanel entityType="track" id="track-1" />);

    // The loading shimmer shows the title first; once the empty result resolves
    // the whole panel is omitted.
    await waitFor(() =>
      expect(screen.queryByText("Sources")).not.toBeInTheDocument(),
    );
  });

  it("shows a single source with its contributed identifier when only one provider contributed", async () => {
    server.use(
      http.get("*/api/v1/tracks/:id/sources", ({ params }) =>
        HttpResponse.json(
          makeSources({
            entity_type: "track",
            entity_id: String(params.id),
            sources: [makeSource({ provider: "musicbrainz", entity_type: "track", isrc: "USQX91300108" })],
          }),
        ),
      ),
    );
    wrap(<SourcesPanel entityType="track" id="track-1" />);

    expect(await screen.findByText("MusicBrainz")).toBeInTheDocument();
    expect(screen.getByText("USQX91300108")).toBeInTheDocument();
  });
});
