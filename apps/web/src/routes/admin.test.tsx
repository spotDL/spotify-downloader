import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import {
  makeAdminStats,
  makePagedReports,
  makeReport,
  makeUser,
} from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";
import { useAuthStore } from "../stores/auth";

// Task 10 — admin-lite is gated by CONTRACT G (`auth && is_admin`). The guard
// warms the ["me"] query and redirects a non-admin; the stats/reports/users
// views render behind it. Report review invalidates the queue + stats caches.

// An access token is required for the guard's token check (the refresh/auth
// interceptor that would attach it is Task 4; here MSW serves /auth/me directly).
function serveMe(isAdmin: boolean) {
  useAuthStore.getState().setAccessToken("test-access-token");
  server.use(
    http.get("*/api/v1/auth/me", () => HttpResponse.json(makeUser({ is_admin: isAdmin }))),
  );
}

beforeEach(() => useAuthStore.getState().reset());
afterEach(() => vi.restoreAllMocks());

describe("Admin guard", () => {
  it("redirects a non-admin away from /admin", async () => {
    serveMe(false);
    renderApp("/admin");

    // Bounced to home — the admin tabs never render.
    expect(await screen.findByText(/Search for a track/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Admin" })).not.toBeInTheDocument();
  });

  it("lets an admin see the stats overview", async () => {
    serveMe(true);
    server.use(http.get("*/api/v1/admin/stats", () => HttpResponse.json(makeAdminStats())));
    renderApp("/admin");

    expect(await screen.findByRole("heading", { name: "Admin" })).toBeInTheDocument();
    expect(await screen.findByText("Users")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });
});

describe("Admin reports", () => {
  it("approving a report invalidates the reports and stats caches", async () => {
    serveMe(true);
    server.use(
      http.get("*/api/v1/admin/reports", () =>
        HttpResponse.json(makePagedReports({ items: [makeReport()] })),
      ),
      http.post("*/api/v1/admin/reports/report-1/approve", () =>
        HttpResponse.json(makeReport({ status: "approved" })),
      ),
    );
    const invalidateSpy = vi.spyOn(QueryClient.prototype, "invalidateQueries");
    const user = userEvent.setup();
    renderApp("/admin/reports");

    await user.click(await screen.findByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["admin", "reports"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["admin", "stats"] });
    });
  });
});
