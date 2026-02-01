import { test, expect } from "@playwright/test";

test.describe("Song Detail Page", () => {
  const mockSong = {
    id: "song-123",
    name: "Bohemian Rhapsody",
    artists: ["Queen"],
    artist: "Queen",
    duration: 355,
    album_name: "A Night at the Opera",
    album_id: "album-456",
    cover_url: "https://example.com/cover.jpg",
    isrc: "GBUM71029604",
    year: 1975,
    platforms: [
      {
        platform: "spotify",
        platform_id: "spotify-123",
        url: "https://open.spotify.com/track/spotify-123",
      },
    ],
    audio_features: {
      bpm: 72,
      energy: 0.4,
      danceability: 0.4,
      valence: 0.2,
      key: 0,
      mode: 1,
      loudness: -10.5,
      speechiness: 0.05,
      acousticness: 0.3,
      instrumentalness: 0.0,
      liveness: 0.3,
      time_signature: 4,
    },
    popularity: 85,
    explicit: false,
    release_date: "1975-10-31",
    label: "EMI",
    copyright_text: "(C) 1975 EMI Records",
    genres: ["Rock", "Progressive Rock"],
    matches_count: 5,
    track_number: 11,
    disc_number: 1,
  };

  const mockLyrics = {
    song_id: "song-123",
    lyrics_text:
      "Is this the real life?\nIs this just fantasy?\nCaught in a landslide\nNo escape from reality",
    lyrics_synced: null,
    source: "genius",
    from_cache: false,
  };

  const mockLyricsNotFound = {
    song_id: "song-456",
    message: "Lyrics not found",
  };

  test.beforeEach(async ({ page }) => {
    // Mock the song API
    await page.route("**/api/v1/entities/songs/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockSong),
      });
    });

    // Mock the lyrics API
    await page.route("**/api/v1/lyrics/song/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockLyrics),
      });
    });
  });

  test("should display song details", async ({ page }) => {
    await page.goto("/song/song-123");

    // Check song name
    await expect(page.getByText("Bohemian Rhapsody")).toBeVisible();

    // Check artist
    await expect(page.getByText("Queen")).toBeVisible();

    // Check album link
    await expect(page.getByText("A Night at the Opera")).toBeVisible();

    // Check duration formatted
    await expect(page.getByText("5:55")).toBeVisible();

    // Check release date
    await expect(page.getByText("1975-10-31")).toBeVisible();
  });

  test("should display genres", async ({ page }) => {
    await page.goto("/song/song-123");

    await expect(page.getByText("Rock")).toBeVisible();
    await expect(page.getByText("Progressive Rock")).toBeVisible();
  });

  test("should display lyrics when available", async ({ page }) => {
    await page.goto("/song/song-123");

    // Check for lyrics heading
    await expect(page.getByText("Lyrics")).toBeVisible();

    // Check for lyrics content
    await expect(page.getByText(/Is this the real life/)).toBeVisible();
  });

  test("should show no lyrics message when lyrics not found", async ({
    page,
  }) => {
    // Override lyrics mock to return not found
    await page.route("**/api/v1/lyrics/song/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockLyricsNotFound),
      });
    });

    await page.goto("/song/song-456");

    await expect(page.getByText(/No lyrics available/i)).toBeVisible();
  });

  test("should display audio features", async ({ page }) => {
    await page.goto("/song/song-123");

    // Check for audio features section
    await expect(page.getByText("Audio Features")).toBeVisible();

    // Check for BPM
    await expect(page.getByText("BPM")).toBeVisible();
    await expect(page.getByText("72")).toBeVisible();

    // Check for Energy
    await expect(page.getByText("Energy")).toBeVisible();
  });

  test("should display key signature badge", async ({ page }) => {
    await page.goto("/song/song-123");

    // C Major (key 0, mode 1)
    await expect(page.getByText(/C Major/i)).toBeVisible();
  });

  test("should display platform links", async ({ page }) => {
    await page.goto("/song/song-123");

    await expect(page.getByText("Listen On")).toBeVisible();
  });

  test("should display technical metadata section", async ({ page }) => {
    await page.goto("/song/song-123");

    // Click to expand technical info
    await page.getByText("Technical Info").click();

    // Check for ISRC
    await expect(page.getByText("ISRC")).toBeVisible();
    await expect(page.getByText("GBUM71029604")).toBeVisible();
  });

  test("should show track and disc number badges", async ({ page }) => {
    await page.goto("/song/song-123");

    await expect(page.getByText(/Track 11/i)).toBeVisible();
  });

  test("should have Find Matches button", async ({ page }) => {
    await page.goto("/song/song-123");

    const findMatchesButton = page.getByRole("button", {
      name: /Find Matches/i,
    });
    await expect(findMatchesButton).toBeVisible();
  });

  test("should display matches after finding them", async ({ page }) => {
    const mockMatches = {
      source_url: "https://open.spotify.com/track/spotify-123",
      matches: [
        {
          id: "match-1",
          source_url: "https://open.spotify.com/track/spotify-123",
          target_url: "https://youtube.com/watch?v=abc",
          target_platform: "youtube",
          score: 95,
          confidence: 0.95,
          match_type: "system",
          result: {
            name: "Bohemian Rhapsody",
            artists: ["Queen"],
            artist: "Queen",
            duration: 355,
            platform: "youtube",
            platform_id: "abc",
            url: "https://youtube.com/watch?v=abc",
            album_name: null,
            cover_url: null,
            views: 1000000,
            explicit: false,
            verified: true,
          },
        },
      ],
      total: 1,
    };

    await page.route("**/api/v1/matches/find*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockMatches),
      });
    });

    await page.goto("/song/song-123");

    // Click Find Matches
    await page.getByRole("button", { name: /Find Matches/i }).click();

    // Wait for matches to load
    await expect(page.getByText("Cross-Platform Matches")).toBeVisible();
    await expect(page.getByText("Best Match")).toBeVisible();
  });

  test("should have Match Manually button", async ({ page }) => {
    await page.goto("/song/song-123");

    await expect(
      page.getByRole("button", { name: /Match Manually/i })
    ).toBeVisible();
  });

  test("should show Report Issue button when authenticated", async ({
    page,
  }) => {
    // Set up authenticated state
    await page.goto("/song/song-123");

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
      page.getByRole("button", { name: /Report Issue/i })
    ).toBeVisible();
  });

  test("should not show Report Issue button when not authenticated", async ({
    page,
  }) => {
    await page.goto("/song/song-123");

    await expect(
      page.getByRole("button", { name: /Report Issue/i })
    ).not.toBeVisible();
  });

  test("should show loading state initially", async ({ page }) => {
    // Add delay to API response
    await page.route("**/api/v1/entities/songs/*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockSong),
      });
    });

    await page.goto("/song/song-123");

    await expect(page.getByText(/Loading track/i)).toBeVisible();
  });

  test("should show error state on API failure", async ({ page }) => {
    await page.route("**/api/v1/entities/songs/*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.goto("/song/song-error");

    await expect(page.getByText(/Failed to load track/i)).toBeVisible();
  });

  test("should show not found state for missing song", async ({ page }) => {
    await page.route("**/api/v1/entities/songs/*", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Song not found" }),
      });
    });

    await page.goto("/song/song-notfound");

    await expect(page.getByText(/Track not found/i)).toBeVisible();
  });

  test("should navigate to album page when clicking album link", async ({
    page,
  }) => {
    await page.goto("/song/song-123");

    const albumLink = page.getByText("A Night at the Opera");
    await albumLink.click();

    await expect(page).toHaveURL(/\/album\/album-456/);
  });

  test("should display copyright info when available", async ({ page }) => {
    await page.goto("/song/song-123");

    await expect(page.getByText("Rights Information")).toBeVisible();
    await expect(page.getByText(/EMI/)).toBeVisible();
  });

  test("should expand and show all audio features", async ({ page }) => {
    await page.goto("/song/song-123");

    // Click show all features
    await page.getByText("Show All Features").click();

    // Check for advanced features
    await expect(page.getByText("Speechiness")).toBeVisible();
    await expect(page.getByText("Acousticness")).toBeVisible();
    await expect(page.getByText("Instrumentalness")).toBeVisible();
    await expect(page.getByText("Liveness")).toBeVisible();
  });
});
