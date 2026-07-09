import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeConfig } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";
import { useAuthStore } from "../stores/auth";
import { useSessionStore } from "../stores/session";

// CONTRACT G — route guards for /login and /register.

beforeEach(() => {
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

afterEach(() => {
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

describe("auth route guards", () => {
  it("redirects an already-authenticated visitor away from /login", async () => {
    useAuthStore.setState({ accessToken: "already-in" });

    renderApp("/login");

    // Bounced to home; the login form never renders.
    expect(await screen.findByLabelText("Paste a link")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("in auth-off mode hides the Sign in nav and redirects /login home", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json(makeConfig({ mode: "embedded" })),
      ),
    );

    renderApp("/login");

    // Redirected home (auth feature off).
    expect(await screen.findByLabelText("Paste a link")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
    // The auth nav affordance is gone.
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });
});
