import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type {
  MatchesResponse,
  VoteResponse,
} from "../api/generated/types.gen";
import { server } from "../test/msw/server";
import { makeConfig, makeMatch, makeMatches } from "../test/msw/fixtures";
import { useAuthStore } from "../stores/auth";
import { renderApp } from "../test/render-app";

function signIn() {
  useAuthStore.getState().setAccessToken("access-token-1");
}

afterEach(() => {
  useAuthStore.getState().reset();
});

const voteOutcome: VoteResponse = {
  upvotes: 5,
  downvotes: 1,
  net_score: 4,
  status: "auto",
  votable_id: "match-1",
  votable_type: "match",
  your_vote: 1,
};

describe("track page", () => {
  it("renders track metadata and its matches", async () => {
    renderApp("/tracks/track-1");

    expect(
      await screen.findByRole("heading", { level: 1, name: "Get Lucky" }),
    ).toBeInTheDocument();
    // Default match fixture candidate name.
    expect(
      await screen.findByText("Get Lucky (Official Audio)"),
    ).toBeInTheDocument();
    // The fixture's 0–100 score (94) must render as "94%", not clamp to 100%:
    // guards the 0–100 wire scale → 0–1 gauge normalization on the track page.
    const meter = await screen.findByRole("meter", { name: "Match score" });
    expect(meter).toHaveAttribute("aria-valuetext", "94%");
  });

  it("invalidates the matches query after a vote", async () => {
    signIn();
    let matchesCalls = 0;
    server.use(
      http.get("*/api/v1/tracks/:id/matches", ({ params }) => {
        matchesCalls += 1;
        return HttpResponse.json<MatchesResponse>(
          makeMatches({ track_id: String(params.id) }),
        );
      }),
      http.post("*/api/v1/matches/:matchId/vote", () =>
        HttpResponse.json(voteOutcome),
      ),
    );

    renderApp("/tracks/track-1");
    await screen.findByText("Get Lucky (Official Audio)");
    await waitFor(() => expect(matchesCalls).toBe(1));

    const user = userEvent.setup();
    // The first Upvote is the match's (the lyrics variant also renders one).
    await user.click(screen.getAllByRole("button", { name: "Upvote" })[0]);

    // The vote's onSuccess invalidates ["track", id, "matches"] → refetch.
    await waitFor(() => expect(matchesCalls).toBe(2));
  });

  it("submits a match URL and refreshes the matches list", async () => {
    signIn();
    let matchesCalls = 0;
    const submit = vi.fn(() =>
      HttpResponse.json(makeMatch({ id: "match-new" }), { status: 201 }),
    );
    server.use(
      http.get("*/api/v1/tracks/:id/matches", ({ params }) => {
        matchesCalls += 1;
        return HttpResponse.json<MatchesResponse>(
          makeMatches({ track_id: String(params.id) }),
        );
      }),
      http.post("*/api/v1/tracks/:id/matches", submit),
    );

    renderApp("/tracks/track-1");
    await screen.findByText("Get Lucky (Official Audio)");
    await waitFor(() => expect(matchesCalls).toBe(1));

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Match URL"),
      "https://youtube.com/watch?v=zzz",
    );
    await user.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(submit).toHaveBeenCalled());
    await waitFor(() => expect(matchesCalls).toBe(2));
  });

  it("hides voting and the submit-match form in embedded mode", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json(makeConfig({ mode: "embedded" })),
      ),
    );

    renderApp("/tracks/track-1");
    await screen.findByText("Get Lucky (Official Audio)");

    expect(
      screen.queryByRole("button", { name: "Upvote" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Match URL")).not.toBeInTheDocument();
  });
});
