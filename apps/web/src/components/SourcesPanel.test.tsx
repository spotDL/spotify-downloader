import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeSource, makeSources } from "../test/msw/fixtures";
import { SourcesPanel, StatsCard } from "./SourcesPanel";

function wrap(node: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{node}</QueryClientProvider>,
  );
}

describe("SourcesPanel", () => {
  it("lists each provider snapshot with its contributed metric", async () => {
    // Default handler serves Spotify + Deezer artist sources.
    wrap(<SourcesPanel entityType="artist" id="artist-1" />);

    expect(await screen.findByText("Spotify")).toBeInTheDocument();
    expect(screen.getByText("Metadata sources")).toBeInTheDocument();
    expect(screen.getByText("Deezer")).toBeInTheDocument();
    // Spotify's 34.2M follower snapshot is shown in mono.
    expect(screen.getByText(/34\.2M/)).toBeInTheDocument();
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
      expect(screen.queryByText("Metadata sources")).not.toBeInTheDocument(),
    );
  });

  it("shows a single source when only one provider contributed", async () => {
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
    expect(screen.getByText(/USQX91300108/)).toBeInTheDocument();
  });
});

describe("StatsCard (Reach)", () => {
  it("compares provider-reported followers with an honest label", async () => {
    wrap(<StatsCard id="artist-1" />);

    expect(await screen.findByText("Reach across platforms")).toBeInTheDocument();
    expect(
      screen.getByText(/not licensed play counts/i),
    ).toBeInTheDocument();
    expect(screen.getByText("34.2M")).toBeInTheDocument();
    expect(screen.getByText("4.5M")).toBeInTheDocument();
  });

  it("renders nothing when no source carries followers", async () => {
    server.use(
      http.get("*/api/v1/artists/:id/sources", ({ params }) =>
        HttpResponse.json(
          makeSources({
            entity_id: String(params.id),
            sources: [makeSource({ provider: "musicbrainz", followers: null })],
          }),
        ),
      ),
    );
    // Render alongside SourcesPanel (same query key): once the panel resolves the
    // shared query has settled, so a missing Reach card is a real omission.
    wrap(
      <>
        <SourcesPanel entityType="artist" id="artist-1" />
        <StatsCard id="artist-1" />
      </>,
    );
    expect(await screen.findByText("MusicBrainz")).toBeInTheDocument();
    expect(screen.queryByText("Reach across platforms")).not.toBeInTheDocument();
  });
});
