import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display the home page with hero section", async ({ page }) => {
    // Check for the main heading
    await expect(
      page.getByRole("heading", { name: /Download Music from/i })
    ).toBeVisible();

    // Check for the description text
    await expect(
      page.getByText(/Enter a song URL from Spotify/i)
    ).toBeVisible();

    // Check for the search input
    await expect(
      page.getByPlaceholder(/Paste a song URL or search/i)
    ).toBeVisible();

    // Check for the search button
    await expect(page.getByRole("button", { name: /Search/i })).toBeVisible();
  });

  test("should display platform badges", async ({ page }) => {
    // Check for platform badges - use exact match to avoid conflicts
    await expect(page.getByText("Spotify", { exact: true })).toBeVisible();
    await expect(page.getByText("Apple Music", { exact: true })).toBeVisible();
    await expect(page.getByText("Deezer", { exact: true })).toBeVisible();
    await expect(page.getByText("YouTube Music", { exact: true })).toBeVisible();
    await expect(page.getByText("SoundCloud", { exact: true })).toBeVisible();
    await expect(page.getByText("Bandcamp", { exact: true })).toBeVisible();
  });

  test("should have empty state message when no search", async ({ page }) => {
    await expect(
      page.getByText(/Enter a song URL above to find download matches/i)
    ).toBeVisible();
  });

  test("should disable search button when input is empty", async ({ page }) => {
    const searchButton = page.getByRole("button", { name: /Search/i });
    await expect(searchButton).toBeDisabled();
  });

  test("should enable search button when input has value", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Paste a song URL or search/i);
    const searchButton = page.getByRole("button", { name: /Search/i });

    await searchInput.fill("https://open.spotify.com/track/123");
    await expect(searchButton).toBeEnabled();
  });

  test("should show loading state when searching", async ({ page }) => {
    // Mock the API to simulate a slow response
    await page.route("**/api/v1/songs/resolve*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          songs: [
            {
              id: "1",
              name: "Test Song",
              artists: ["Test Artist"],
              artist: "Test Artist",
              platform: "spotify",
              platform_id: "123",
              duration: 180,
              album_name: "Test Album",
              url: "https://open.spotify.com/track/123",
              isrc: null,
            },
          ],
          total: 1,
        }),
      });
    });

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
            artist: "Test Artist",
            platform: "spotify",
            platform_id: "123",
            duration: 180,
            url: "https://open.spotify.com/track/123",
          },
          matches: [],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Paste a song URL or search/i);
    const searchButton = page.getByRole("button", { name: /Search/i });

    await searchInput.fill("https://open.spotify.com/track/123");
    await searchButton.click();

    // Should show loading state
    await expect(page.getByText(/Searching for matches/i)).toBeVisible();
  });

  test("should display song result after successful search", async ({
    page,
  }) => {
    // Mock the resolve API
    await page.route("**/api/v1/songs/resolve*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          songs: [
            {
              id: "1",
              name: "Bohemian Rhapsody",
              artists: ["Queen"],
              artist: "Queen",
              platform: "spotify",
              platform_id: "123",
              duration: 355,
              album_name: "A Night at the Opera",
              url: "https://open.spotify.com/track/123",
              isrc: null,
            },
          ],
          total: 1,
        }),
      });
    });

    // Mock the matches API
    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Bohemian Rhapsody",
            artists: ["Queen"],
            artist: "Queen",
            platform: "spotify",
            platform_id: "123",
            duration: 355,
            url: "https://open.spotify.com/track/123",
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "auto",
              upvotes: 10,
              downvotes: 2,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Paste a song URL or search/i);
    const searchButton = page.getByRole("button", { name: /Search/i });

    await searchInput.fill("https://open.spotify.com/track/123");
    await searchButton.click();

    // Wait for results
    await expect(page.getByText("Bohemian Rhapsody")).toBeVisible();
    await expect(page.getByText("Queen")).toBeVisible();
    await expect(page.getByText("5:55")).toBeVisible(); // 355 seconds formatted
  });

  test("should display matches after successful search", async ({ page }) => {
    // Mock APIs
    await page.route("**/api/v1/songs/resolve*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          songs: [
            {
              id: "1",
              name: "Test Song",
              artists: ["Test Artist"],
              artist: "Test Artist",
              platform: "spotify",
              platform_id: "123",
              duration: 180,
              url: "https://open.spotify.com/track/123",
              isrc: null,
            },
          ],
          total: 1,
        }),
      });
    });

    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          song: {
            id: "1",
            name: "Test Song",
            artists: ["Test Artist"],
            artist: "Test Artist",
            platform: "spotify",
            platform_id: "123",
            duration: 180,
            url: "https://open.spotify.com/track/123",
          },
          matches: [
            {
              id: "m1",
              target_platform: "youtube",
              target_url: "https://youtube.com/watch?v=abc",
              match_score: 95,
              match_type: "auto",
              upvotes: 10,
              downvotes: 2,
            },
            {
              id: "m2",
              target_platform: "soundcloud",
              target_url: "https://soundcloud.com/test/song",
              match_score: 85,
              match_type: "user",
              upvotes: 5,
              downvotes: 1,
            },
          ],
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Paste a song URL or search/i);
    await searchInput.fill("https://open.spotify.com/track/123");
    await page.getByRole("button", { name: /Search/i }).click();

    // Check for matches header
    await expect(page.getByText(/Found 2 matches/i)).toBeVisible();

    // Check for match scores
    await expect(page.getByText("95% match")).toBeVisible();
    await expect(page.getByText("85% match")).toBeVisible();

    // Check for Download buttons (one for each match) - canDownload is true in self-hosted mode
    const downloadButtons = page.getByRole("button", { name: /Download/i });
    await expect(downloadButtons).toHaveCount(2);
  });

  test("should display error message on API failure", async ({ page }) => {
    // Mock API to return error
    await page.route("**/api/v1/songs/resolve*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    const searchInput = page.getByPlaceholder(/Paste a song URL or search/i);
    await searchInput.fill("https://open.spotify.com/track/invalid");
    await page.getByRole("button", { name: /Search/i }).click();

    // Should show error message - looking for the "Search failed" text
    await expect(page.getByText(/Search failed/i)).toBeVisible();
  });
});
