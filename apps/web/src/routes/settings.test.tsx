import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import * as sdk from "../api/generated/sdk.gen";
import { server } from "../test/msw/server";
import { makeConfig, makeDownloadDefaults } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";
import { useSessionStore } from "../stores/session";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";

// Task 10 — Settings is a client/prefs surface plus a READ-ONLY window onto the
// server's startup config. The base-URL field is the one runtime lever
// (CONTRACT B): it persists to the session store and clears the query cache.

beforeEach(() => {
  useSessionStore.getState().setApiBaseUrl("");
  useAuthStore.getState().reset();
  useUiStore.getState().setTheme("system");
});

afterEach(() => vi.restoreAllMocks());

describe("Settings — server config (read-only)", () => {
  it("surfaces the mode, matcher version, and feature flags", async () => {
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });

    expect(screen.getByText("selfhost")).toBeInTheDocument();
    expect(screen.getByText("1.0.0")).toBeInTheDocument();
    // selfhost → downloads + library on (fixtures MODE_FLAGS). Scope to the
    // <dt> so we don't collide with the nav's "Downloads" link.
    const downloadsRow = screen.getByText("Downloads", { selector: "dt" }).closest("div");
    expect(downloadsRow).toHaveTextContent("On");
  });

  it("hides download defaults when the server reports none (hosted-style)", async () => {
    // Default fixture config has download_defaults: null.
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });
    expect(screen.queryByText("Download defaults")).not.toBeInTheDocument();
  });

  it("shows download defaults when the server provides them", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json(makeConfig({ download_defaults: makeDownloadDefaults() })),
      ),
    );
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });

    expect(screen.getByText("Download defaults")).toBeInTheDocument();
    expect(screen.getByText("{artists} - {title}.{output-ext}")).toBeInTheDocument();
  });

  it("has no config mutation — the server config is immutable by construction", () => {
    // There is no PUT/POST/PATCH/DELETE operation touching /config in the
    // generated SDK, so the read-only panel could not mutate config even if it
    // tried. This is the structural guarantee behind the "read-only" claim.
    const mutatesConfig = Object.keys(sdk).some(
      (name) => /config/i.test(name) && /(post|put|patch|delete)/i.test(name),
    );
    expect(mutatesConfig).toBe(false);
  });
});

describe("Settings — API base URL", () => {
  it("persists the base URL and clears the query cache on save", async () => {
    const clearSpy = vi.spyOn(QueryClient.prototype, "clear");
    const user = userEvent.setup();
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });

    const field = screen.getByLabelText("API base URL");
    await user.type(field, "https://nas.local:7070");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(useSessionStore.getState().apiBaseUrl).toBe("https://nas.local:7070");
    expect(clearSpy).toHaveBeenCalled();
  });

  it("test connection probes health at the configured base URL", async () => {
    server.use(http.get("*/api/v1/health", () => HttpResponse.json({ status: "ok" })));
    const user = userEvent.setup();
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });

    await user.type(screen.getByLabelText("API base URL"), "https://nas.local:7070");
    await user.click(screen.getByRole("button", { name: "Test connection" }));

    expect(await screen.findByText("Connected")).toBeInTheDocument();
  });

  it("rejects a non-URL base and keeps Save disabled", async () => {
    const user = userEvent.setup();
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });

    await user.type(screen.getByLabelText("API base URL"), "not a url");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(useSessionStore.getState().apiBaseUrl).toBe("");
  });
});

describe("Settings — appearance", () => {
  it("writes the chosen theme to the UI store", async () => {
    const user = userEvent.setup();
    renderApp("/settings");
    await screen.findByRole("heading", { name: "Settings" });

    await user.click(screen.getByRole("radio", { name: "Dark" }));
    await waitFor(() => expect(useUiStore.getState().theme).toBe("dark"));
  });
});
