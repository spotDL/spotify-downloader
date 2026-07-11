import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { toast } from "../components/Toasts";
import { renderApp } from "../test/render-app";
import { meQueryKey } from "../api/mutations";
import { useAuthStore } from "../stores/auth";
import { useSessionStore } from "../stores/session";

// Task 4 — OAuth fragment callback (CONTRACT C). The route reads the URL FRAGMENT
// only, stores tokens (or toasts an error), strips the fragment, and navigates.

function setHash(hash: string) {
  window.history.replaceState(null, "", `/auth/callback/github${hash}`);
}

beforeEach(() => {
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

describe("oauth callback", () => {
  it("stores fragment tokens, invalidates ['me'], strips the fragment, and lands home", async () => {
    setHash("#access_token=acc-oauth&refresh_token=ref-oauth&token_type=bearer&expires_in=900");

    const { queryClient } = renderApp("/auth/callback/github");
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    await waitFor(() =>
      expect(useAuthStore.getState().accessToken).toBe("acc-oauth"),
    );
    expect(useSessionStore.getState().refreshToken).toBe("ref-oauth");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: meQueryKey() });
    // Fragment stripped from the URL bar / history.
    expect(window.location.hash).toBe("");
    // Navigated home.
    expect(await screen.findByLabelText("Paste a link")).toBeInTheDocument();
  });

  it("toasts and redirects to /login on #error, stripping the fragment", async () => {
    setHash("#error=oauth_state_mismatch");
    // The toast shim delegates to sonner, whose viewport animates toasts in via
    // timers jsdom never fires — assert the shim call instead of toast DOM.
    const pushSpy = vi.spyOn(toast, "push");

    renderApp("/auth/callback/github");

    await waitFor(() =>
      expect(pushSpy).toHaveBeenCalledWith(
        "Sign-in failed (oauth_state_mismatch).",
        "error",
      ),
    );
    pushSpy.mockRestore();
    expect(window.location.hash).toBe("");
    expect(useAuthStore.getState().accessToken).toBeNull();
    // Redirected to the login page.
    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("treats an empty hash as an invalid callback (toast + /login)", async () => {
    setHash("");

    renderApp("/auth/callback/github");

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("ignores tokens supplied as query params (fragment-only)", async () => {
    // Tokens in the query string must NOT be consumed.
    window.history.replaceState(
      null,
      "",
      "/auth/callback/github?access_token=query-acc&refresh_token=query-ref",
    );

    renderApp("/auth/callback/github");

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useSessionStore.getState().refreshToken).toBeNull();
  });
});
