import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeToken } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";
import { meQueryKey } from "../api/mutations";
import { useAuthStore } from "../stores/auth";
import { useSessionStore } from "../stores/session";

// Task 4 — login page (CONTRACT C/D). Selfhost config (auth on) is the default
// MSW fixture, so the guard lets the page render.

beforeEach(() => {
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

afterEach(() => {
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

async function fillAndSubmit() {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Email"), "user@example.com");
  await user.type(screen.getByLabelText("Password"), "hunter2");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("login page", () => {
  it("stores the token pair, invalidates ['me'], and lands home on success", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json(
          makeToken({ access_token: "acc-1", refresh_token: "ref-1" }),
        ),
      ),
    );

    const { queryClient } = renderApp("/login");
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await fillAndSubmit();

    await waitFor(() =>
      expect(useAuthStore.getState().accessToken).toBe("acc-1"),
    );
    expect(useSessionStore.getState().refreshToken).toBe("ref-1");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: meQueryKey() });
    // Landed on home (the paste-a-link field is unique to the home route).
    expect(await screen.findByLabelText("Paste a link")).toBeInTheDocument();
  });

  it("toasts on invalid_credentials and stays anonymous", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json(
          { code: "invalid_credentials", message: "bad", detail: null },
          { status: 401 },
        ),
      ),
    );

    renderApp("/login");
    await fillAndSubmit();

    expect(
      await screen.findByText("Wrong email or password."),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
