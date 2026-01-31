import { test, expect } from "@playwright/test";

test.describe("Matching Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/matching");
  });

  test("should display the matching page header", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Match Voting/i })
    ).toBeVisible();
    await expect(
      page.getByText(/Help improve match quality by voting on song matches/i)
    ).toBeVisible();
  });

  test("should show auth warning when not logged in", async ({ page }) => {
    await expect(
      page.getByText(/Sign in to vote on matches and contribute/i)
    ).toBeVisible();
  });

  test("should not show auth warning when logged in", async ({ page }) => {
    // Set up authenticated state
    await page.evaluate(() => {
      const authState = {
        state: {
          user: { id: "1", username: "testuser", email: "test@example.com" },
          accessToken: "test-token",
          isAuthenticated: true,
        },
        version: 0,
      };
      localStorage.setItem("auth-storage", JSON.stringify(authState));
    });

    await page.reload();

    await expect(
      page.getByText(/Sign in to vote on matches and contribute/i)
    ).not.toBeVisible();
  });

  test("should display search form", async ({ page }) => {
    await expect(
      page.getByPlaceholder(/Enter a song URL to see matches/i)
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Find Matches/i })
    ).toBeVisible();
  });

  test("should disable search button when input is empty", async ({ page }) => {
    const searchButton = page.getByRole("button", { name: /Find Matches/i });
    await expect(searchButton).toBeDisabled();
  });

  test("should enable search button when input has value", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    const searchButton = page.getByRole("button", { name: /Find Matches/i });

    await searchInput.fill("https://open.spotify.com/track/123");
    await expect(searchButton).toBeEnabled();
  });

  test("should show loading state when searching", async ({ page }) => {
    // Mock slow API response
    await page.route("**/api/v1/matches/find*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText(/Finding matches/i)).toBeVisible();
  });

  test("should display song info after search", async ({ page }) => {
    // Mock API
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Stairway to Heaven",
            artists: ["Led Zeppelin"],
            platform: "spotify",
            duration_seconds: 482,
          },
          matches: [],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText("Stairway to Heaven")).toBeVisible();
    await expect(page.getByText("Led Zeppelin")).toBeVisible();
    await expect(page.getByText("8:02")).toBeVisible(); // 482 seconds
  });

  test("should display matches with vote counts", async ({ page }) => {
    // Mock API
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "auto",
              upvotes: 25,
              downvotes: 3,
            },
            {
              id: "m2",
              target_platform: "soundcloud",
              target_url: "https://soundcloud.com/test/song",
              match_score: 88,
              match_type: "user",
              upvotes: 10,
              downvotes: 2,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    // Wait for results
    await expect(page.getByText("2 Matches Found")).toBeVisible();

    // Check for platforms
    await expect(page.getByText("youtube")).toBeVisible();
    await expect(page.getByText("soundcloud")).toBeVisible();

    // Check for match scores
    await expect(page.getByText("95% confidence")).toBeVisible();
    await expect(page.getByText("88% confidence")).toBeVisible();

    // Check for vote counts
    await expect(page.getByText(/25/)).toBeVisible();
    await expect(page.getByText(/10/)).toBeVisible();
  });

  test("should show user submitted badge for user matches", async ({
    page,
  }) => {
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "user",
              upvotes: 5,
              downvotes: 0,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText("User Submitted")).toBeVisible();
  });

  test("should show no results message when no matches found", async ({
    page,
  }) => {
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Rare Song",
            artists: ["Unknown Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/rare");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText("No matches found for this song")).toBeVisible();
  });

  test("should display error on API failure", async ({ page }) => {
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/error");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.locator(".text-red-400")).toBeVisible();
  });

  test("should have vote buttons on matches", async ({ page }) => {
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "auto",
              upvotes: 5,
              downvotes: 1,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    // Wait for results
    await expect(page.getByText("1 Match Found")).toBeVisible();

    // Check for upvote and downvote buttons (SVG icons)
    const voteButtons = page.locator('button[title*="vote"]');
    await expect(voteButtons).toHaveCount(2);
  });

  test("should disable vote buttons when not logged in", async ({ page }) => {
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "auto",
              upvotes: 5,
              downvotes: 1,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText("1 Match Found")).toBeVisible();

    // Vote buttons should have "Sign in to vote" title
    const voteButtons = page.locator('button[title="Sign in to vote"]');
    await expect(voteButtons).toHaveCount(2);
  });

  test("should enable vote buttons when logged in", async ({ page }) => {
    // Set up authenticated state
    await page.evaluate(() => {
      const authState = {
        state: {
          user: { id: "1", username: "testuser", email: "test@example.com" },
          accessToken: "test-token",
          isAuthenticated: true,
        },
        version: 0,
      };
      localStorage.setItem("auth-storage", JSON.stringify(authState));
    });

    await page.reload();

    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "auto",
              upvotes: 5,
              downvotes: 1,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText("1 Match Found")).toBeVisible();

    // Vote buttons should have proper titles
    await expect(page.locator('button[title="Upvote"]')).toBeVisible();
    await expect(page.locator('button[title="Downvote"]')).toBeVisible();
  });

  test("should rank matches by net votes", async ({ page }) => {
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            platform: "spotify",
            duration_seconds: 180,
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=low",
              match_score: 95,
              match_type: "auto",
              upvotes: 2,
              downvotes: 5, // net -3
            },
            {
              id: "m2",
              target_platform: "soundcloud",
              target_url: "https://soundcloud.com/high",
              match_score: 80,
              match_type: "user",
              upvotes: 20,
              downvotes: 2, // net +18
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Enter a song URL to see matches/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Find Matches/i }).click();

    await expect(page.getByText("2 Matches Found")).toBeVisible();

    // First match should be soundcloud (higher net votes)
    const ranks = page.locator('text="#1"');
    const firstRank = ranks.first();
    await expect(firstRank).toBeVisible();

    // The soundcloud match should appear first
    const matchCards = page.locator('[class*="hover:border-gray-600"]');
    const firstCard = matchCards.first();
    await expect(firstCard.getByText("soundcloud")).toBeVisible();
  });
});
