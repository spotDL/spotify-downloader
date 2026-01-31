import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Mock health endpoint for consistent Online/Offline status
    await page.route("**/api/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "healthy" }),
      });
    });

    await page.goto("/");
  });

  test("should display navigation bar", async ({ page }) => {
    const nav = page.locator("nav");
    await expect(nav).toBeVisible();

    // Check for logo/brand
    await expect(nav.getByText("SpotDL")).toBeVisible();

    // Check for navigation links
    await expect(nav.getByRole("link", { name: /Home/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /Queue/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /Matching/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /Settings/i })).toBeVisible();
  });

  test("should show online/offline status badge", async ({ page }) => {
    // The health endpoint is mocked to return healthy, so it should show Online
    await expect(page.getByText("Online")).toBeVisible();
  });

  test("should show offline badge when API is down", async ({ page }) => {
    // Override health endpoint to fail
    await page.route("**/api/health", async (route) => {
      await route.abort("connectionfailed");
    });

    await page.reload();

    // Should show Offline badge
    await expect(page.getByText("Offline")).toBeVisible();
  });

  test("should navigate to Home page", async ({ page }) => {
    await page.goto("/settings");
    await page.locator("nav").getByRole("link", { name: /Home/i }).click();

    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("heading", { name: /Download Music from/i })
    ).toBeVisible();
  });

  test("should navigate to Queue page", async ({ page }) => {
    await page.locator("nav").getByRole("link", { name: /Queue/i }).click();

    await expect(page).toHaveURL("/queue");
    await expect(
      page.getByRole("heading", { name: /Download Queue/i })
    ).toBeVisible();
  });

  test("should navigate to Matching page", async ({ page }) => {
    await page.locator("nav").getByRole("link", { name: /Matching/i }).click();

    await expect(page).toHaveURL("/matching");
    await expect(
      page.getByRole("heading", { name: /Match Voting/i })
    ).toBeVisible();
  });

  test("should navigate to Settings page", async ({ page }) => {
    await page.locator("nav").getByRole("link", { name: /Settings/i }).click();

    await expect(page).toHaveURL("/settings");
    await expect(
      page.getByRole("heading", { name: /Settings/i })
    ).toBeVisible();
  });

  test("should highlight active navigation link", async ({ page }) => {
    // On home page, Home link should be active
    const homeLink = page.locator("nav").getByRole("link", { name: /Home/i });
    await expect(homeLink).toHaveClass(/active/);

    // Navigate to queue
    await page.locator("nav").getByRole("link", { name: /Queue/i }).click();
    const queueLink = page.locator("nav").getByRole("link", { name: /Queue/i });
    await expect(queueLink).toHaveClass(/active/);
  });

  test("should display footer", async ({ page }) => {
    const footer = page.locator("footer");
    await expect(footer).toBeVisible();

    // Check for version info
    await expect(footer.getByText(/SpotDL v5.0.0/i)).toBeVisible();

    // Check for GitHub link
    await expect(footer.getByRole("link", { name: /GitHub/i })).toBeVisible();
  });

  test("should open GitHub link in new tab", async ({ page }) => {
    const githubLink = page.locator("footer").getByRole("link", { name: /GitHub/i });

    await expect(githubLink).toHaveAttribute("target", "_blank");
    await expect(githubLink).toHaveAttribute("rel", /noopener/);
    await expect(githubLink).toHaveAttribute(
      "href",
      "https://github.com/spotDL/spotify-downloader"
    );
  });

  test("should navigate using browser back/forward", async ({ page }) => {
    // Start at home
    await expect(page).toHaveURL("/");

    // Navigate to queue
    await page.locator("nav").getByRole("link", { name: /Queue/i }).click();
    await expect(page).toHaveURL("/queue");

    // Navigate to settings
    await page.locator("nav").getByRole("link", { name: /Settings/i }).click();
    await expect(page).toHaveURL("/settings");

    // Go back to queue
    await page.goBack();
    await expect(page).toHaveURL("/queue");

    // Go back to home
    await page.goBack();
    await expect(page).toHaveURL("/");

    // Go forward to queue
    await page.goForward();
    await expect(page).toHaveURL("/queue");
  });

  test("clicking logo should navigate to home", async ({ page }) => {
    await page.goto("/settings");

    const logo = page.locator("nav").getByRole("link", { name: /SpotDL/i });
    await logo.click();

    await expect(page).toHaveURL("/");
  });
});
