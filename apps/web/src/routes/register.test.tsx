import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { makeToken } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";
import { useAuthStore } from "../stores/auth";
import { useSessionStore } from "../stores/session";

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
  await user.type(await screen.findByLabelText("Email"), "new@example.com");
  await user.type(screen.getByLabelText("Password"), "hunter2000");
  await user.click(screen.getByRole("button", { name: "Create account" }));
}

describe("register page", () => {
  it("stores tokens and lands home on success", async () => {
    server.use(
      http.post("*/api/v1/auth/register", () =>
        HttpResponse.json(
          makeToken({ access_token: "acc-r", refresh_token: "ref-r" }),
        ),
      ),
      http.get("*/api/v1/auth/me", () =>
        HttpResponse.json({
          id: "u2",
          email: "new@example.com",
          display_name: null,
          is_admin: false,
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );

    renderApp("/register");
    await fillAndSubmit();

    await waitFor(() =>
      expect(useAuthStore.getState().accessToken).toBe("acc-r"),
    );
    expect(useSessionStore.getState().refreshToken).toBe("ref-r");
  });

  it("toasts on email_taken", async () => {
    server.use(
      http.post("*/api/v1/auth/register", () =>
        HttpResponse.json(
          { code: "email_taken", message: "taken", detail: null },
          { status: 409 },
        ),
      ),
    );

    renderApp("/register");
    await fillAndSubmit();

    expect(
      await screen.findByText(
        "An account with that email already exists — sign in instead.",
      ),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
