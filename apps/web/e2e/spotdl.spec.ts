import { expect, test } from "@playwright/test";

// These mirror the SEED_* constants in apps/server/scripts/serve_e2e.py. The
// server seeds two accounts, a canonical track with a community match, and one
// completed download before Playwright starts.
const ADMIN = { email: "admin@example.com", password: "admin-password-123" };
const LISTENER = { email: "listener@example.com", password: "listener-password-123" };
const TRACK_URL = "https://open.spotify.com/track/e2etrack01";
const TRACK_NAME = "E2E Anthem";

async function signIn(
  page: import("@playwright/test").Page,
  creds: { email: string; password: string },
) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(creds.email);
  await page.getByLabel("Password").fill(creds.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  // login's onSuccess navigates home.
  await expect(page).toHaveURL(/\/$/);
}

test("mode-gated nav: selfhost shows Downloads + Library, hides Admin when signed out", async ({
  page,
}) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Primary" });
  await expect(nav.getByRole("link", { name: "Downloads" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Library" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Settings" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Sign in" })).toBeVisible();
  // Admin is is_admin-gated: absent for an anonymous visitor.
  await expect(nav.getByRole("link", { name: "Admin" })).toHaveCount(0);
});

test("search renders provider results", async ({ page }) => {
  await page.goto("/search?q=anthem");
  await expect(page.getByText(TRACK_NAME)).toBeVisible();
});

test("sign in, open the track, and upvote its match", async ({ page }) => {
  await signIn(page, LISTENER);

  // Resolve the seeded track URL from the home page — the app navigates to the
  // canonical track page (the same entity the match was seeded on).
  await page.getByLabel("Paste a link").fill(TRACK_URL);
  await page.getByRole("button", { name: "Open" }).click();

  await expect(
    page.getByRole("heading", { level: 1, name: TRACK_NAME }),
  ).toBeVisible();

  // The match row's vote control (the lyrics viewer renders more, so take the
  // first). An anonymous visitor sees it disabled; signed in it votes.
  const upvote = page.getByRole("button", { name: "Upvote" }).first();
  await expect(upvote).toBeEnabled();
  await upvote.click();
  await expect(upvote).toHaveAttribute("aria-pressed", "true");
});

test("the library lists the completed download with a file link", async ({
  page,
}) => {
  await page.goto("/library");
  await expect(page.getByRole("heading", { name: "Library" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Download" }).first(),
  ).toBeVisible();
});

test("admin signs in, the Admin nav appears, and stats render", async ({
  page,
}) => {
  await signIn(page, ADMIN);

  const adminLink = page.getByRole("navigation", { name: "Primary" }).getByRole(
    "link",
    { name: "Admin" },
  );
  await expect(adminLink).toBeVisible();
  await adminLink.click();

  await expect(page).toHaveURL(/\/admin/);
  // The stats dashboard cards (AdminStatsResponse).
  await expect(page.getByText("Users", { exact: true })).toBeVisible();
  await expect(page.getByText("Matches", { exact: true })).toBeVisible();
});
