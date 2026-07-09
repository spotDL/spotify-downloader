import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeConfig } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";
import { useSessionStore } from "../stores/session";

// CONTRACT G — the ConfigGate suspends on GET /config, shows a recoverable
// "can't reach the server" screen (with the base-URL field) on error, and only
// renders the router once config resolves.

beforeEach(() => {
  useSessionStore.getState().setApiBaseUrl("");
});

describe("ConfigGate", () => {
  it("renders the app shell once /config resolves", async () => {
    // Default handler serves a selfhost config.
    renderApp();
    expect(await screen.findByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  });

  it("shows the recovery screen with a base-URL field when /config fails", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json({ error: { code: "internal_error", message: "boom" } }, { status: 500 }),
      ),
    );
    renderApp();

    expect(await screen.findByText("Can't reach the server")).toBeInTheDocument();
    expect(screen.getByLabelText("API base URL")).toBeInTheDocument();
    // The router (and its nav) must NOT have rendered.
    expect(screen.queryByRole("navigation", { name: "Primary" })).not.toBeInTheDocument();
  });

  it("writes the entered base URL to the session store and retries", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json({ error: { code: "internal_error", message: "boom" } }, { status: 500 }),
      ),
    );
    renderApp();

    const field = await screen.findByLabelText("API base URL");
    await user.type(field, "https://nas.local:7070");

    // The retry succeeds once the server is reachable again.
    server.use(http.get("*/api/v1/config", () => HttpResponse.json(makeConfig())));
    await user.click(screen.getByRole("button", { name: "Retry connection" }));

    // The form stores the raw (trimmed) value; resolveHttpBase does the
    // trailing-slash normalization at request time (base-url.test.ts).
    expect(useSessionStore.getState().apiBaseUrl).toBe("https://nas.local:7070");
    await waitFor(() =>
      expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument(),
    );
  });
});
