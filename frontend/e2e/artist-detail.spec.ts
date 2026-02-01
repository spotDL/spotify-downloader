import { test, expect } from "@playwright/test";

test.describe("Artist Detail Page", () => {
  const mockArtist = {
    id: "artist-123",
    name: "Queen",
    image_url: "https://example.com/queen.jpg",
    genres: ["Rock", "Classic Rock", "Glam Rock"],
    platforms: [
      {
        platform: "spotify",
        platform_id: "spotify-artist-123",
        url: "https://open.spotify.com/artist/spotify-artist-123",
        followers: 42000000,
      },
    ],
    albums: [
      {
        id: "album-1",
        name: "A Night at the Opera",
        cover_url: "https://example.com/opera.jpg",
        year: 1975,
        total_tracks: 12,
        album_type: "album",
      },
      {
        id: "album-2",
        name: "News of the World",
        cover_url: "https://example.com/news.jpg",
        year: 1977,
        total_tracks: 11,
        album_type: "album",
      },
      {
        id: "single-1",
        name: "Bohemian Rhapsody",
        cover_url: "https://example.com/br-single.jpg",
        year: 1975,
        total_tracks: 1,
        album_type: "single",
      },
    ],
    songs: [
      {
        id: "song-1",
        name: "Bohemian Rhapsody",
        artists: ["Queen"],
        artist: "Queen",
        duration: 355,
        album_name: "A Night at the Opera",
        album_id: "album-1",
        cover_url: "https://example.com/cover1.jpg",
        isrc: "GBUM71029604",
        year: 1975,
        platforms: [
          {
            platform: "spotify",
            platform_id: "sp-song-1",
            url: "https://open.spotify.com/track/sp-song-1",
          },
        ],
      },
      {
        id: "song-2",
        name: "We Will Rock You",
        artists: ["Queen"],
        artist: "Queen",
        duration: 122,
        album_name: "News of the World",
        album_id: "album-2",
        cover_url: "https://example.com/cover2.jpg",
        isrc: "GBUM71029605",
        year: 1977,
        platforms: [
          {
            platform: "spotify",
            platform_id: "sp-song-2",
            url: "https://open.spotify.com/track/sp-song-2",
          },
        ],
      },
      {
        id: "song-3",
        name: "We Are the Champions",
        artists: ["Queen"],
        artist: "Queen",
        duration: 180,
        album_name: "News of the World",
        album_id: "album-2",
        cover_url: "https://example.com/cover3.jpg",
        isrc: "GBUM71029606",
        year: 1977,
        platforms: [
          {
            platform: "spotify",
            platform_id: "sp-song-3",
            url: "https://open.spotify.com/track/sp-song-3",
          },
        ],
      },
    ],
    total_albums: 15,
    total_songs: 200,
    monthly_listeners: 42000000,
    popularity: 85,
    bio: "Queen is a British rock band formed in London in 1970. The band consisted of Freddie Mercury, Brian May, Roger Taylor and John Deacon.",
    origin_country: "United Kingdom",
    origin_city: "London",
    formed_year: 1970,
    related_artists: [
      {
        id: "related-1",
        name: "David Bowie",
        image_url: "https://example.com/bowie.jpg",
        genres: ["Rock", "Art Rock"],
      },
      {
        id: "related-2",
        name: "Led Zeppelin",
        image_url: "https://example.com/zeppelin.jpg",
        genres: ["Rock", "Hard Rock"],
      },
    ],
  };

  test.beforeEach(async ({ page }) => {
    // Mock the artist API
    await page.route("**/api/v1/entities/artists/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockArtist),
      });
    });
  });

  test("should display artist name and image", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(
      page.getByRole("heading", { name: "Queen", level: 1 })
    ).toBeVisible();
  });

  test("should display artist badge", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Artist", { exact: true })).toBeVisible();
  });

  test("should display origin information", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText(/London, United Kingdom/)).toBeVisible();
    await expect(page.getByText(/Active since 1970/)).toBeVisible();
  });

  test("should display genres", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Rock")).toBeVisible();
    await expect(page.getByText("Classic Rock")).toBeVisible();
    await expect(page.getByText("Glam Rock")).toBeVisible();
  });

  test("should display monthly listeners and popularity", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Monthly Listeners")).toBeVisible();
    await expect(page.getByText("42M")).toBeVisible();
    await expect(page.getByText("85")).toBeVisible();
  });

  test("should display song and album counts", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Songs")).toBeVisible();
    await expect(page.getByText("Albums")).toBeVisible();
  });

  test("should display platform links", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Listen On")).toBeVisible();
  });

  test("should display bio in About section", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("About")).toBeVisible();
    await expect(
      page.getByText(/Queen is a British rock band formed in London/)
    ).toBeVisible();
  });

  test("should display related artists", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Related Artists")).toBeVisible();
    await expect(page.getByText("David Bowie")).toBeVisible();
    await expect(page.getByText("Led Zeppelin")).toBeVisible();
  });

  test("should display discography section", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Discography")).toBeVisible();
    await expect(page.getByText("A Night at the Opera")).toBeVisible();
    await expect(page.getByText("News of the World")).toBeVisible();
  });

  test("should display album type filter tabs", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByRole("button", { name: "All" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Albums" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Singles" })).toBeVisible();
  });

  test("should filter albums by type", async ({ page }) => {
    await page.goto("/artist/artist-123");

    // Click Singles filter
    await page.getByRole("button", { name: "Singles" }).click();

    // Should show single
    await expect(page.getByText("Bohemian Rhapsody")).toBeVisible();
  });

  test("should display top tracks section", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(page.getByText("Top Tracks")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Bohemian Rhapsody" })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "We Will Rock You" })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "We Are the Champions" })
    ).toBeVisible();
  });

  test("should display track numbers in top tracks", async ({ page }) => {
    await page.goto("/artist/artist-123");

    // Check for track numbering
    await expect(page.getByText("01")).toBeVisible();
    await expect(page.getByText("02")).toBeVisible();
    await expect(page.getByText("03")).toBeVisible();
  });

  test("should show track durations", async ({ page }) => {
    await page.goto("/artist/artist-123");

    // Bohemian Rhapsody is 355 seconds = 5:55
    await expect(page.getByText("5:55")).toBeVisible();
    // We Will Rock You is 122 seconds = 2:02
    await expect(page.getByText("2:02")).toBeVisible();
  });

  test("should have Download All Songs button", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await expect(
      page.getByRole("button", { name: /Download All Songs/i })
    ).toBeVisible();
  });

  test("should show Report Issue button when authenticated", async ({
    page,
  }) => {
    await page.goto("/artist/artist-123");

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

  test("should navigate to song page when clicking track", async ({ page }) => {
    await page.goto("/artist/artist-123");

    await page.getByRole("link", { name: "Bohemian Rhapsody" }).click();

    await expect(page).toHaveURL(/\/song\/song-1/);
  });

  test("should navigate to album page when clicking album", async ({
    page,
  }) => {
    await page.goto("/artist/artist-123");

    await page.getByRole("link", { name: "A Night at the Opera" }).click();

    await expect(page).toHaveURL(/\/album\/album-1/);
  });

  test("should navigate to related artist page", async ({ page }) => {
    // Mock the second artist
    await page.route("**/api/v1/entities/artists/related-1", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...mockArtist,
          id: "related-1",
          name: "David Bowie",
        }),
      });
    });

    await page.goto("/artist/artist-123");

    await page.getByRole("link", { name: "David Bowie" }).click();

    await expect(page).toHaveURL(/\/artist\/related-1/);
  });

  test("should show loading state initially", async ({ page }) => {
    await page.route("**/api/v1/entities/artists/*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockArtist),
      });
    });

    await page.goto("/artist/artist-123");

    await expect(page.getByText(/Loading artist/i)).toBeVisible();
  });

  test("should show error state on API failure", async ({ page }) => {
    await page.route("**/api/v1/entities/artists/*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.goto("/artist/artist-error");

    await expect(page.getByText(/Failed to load artist/i)).toBeVisible();
  });

  test("should show not found state for missing artist", async ({ page }) => {
    await page.route("**/api/v1/entities/artists/*", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Artist not found" }),
      });
    });

    await page.goto("/artist/artist-notfound");

    await expect(page.getByText(/Artist not found/i)).toBeVisible();
  });

  test("should expand bio on Read more click", async ({ page }) => {
    // Override with long bio
    await page.route("**/api/v1/entities/artists/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...mockArtist,
          bio: "Queen is a British rock band formed in London in 1970. ".repeat(
            20
          ),
        }),
      });
    });

    await page.goto("/artist/artist-123");

    // Should show Read more button for long bio
    const readMoreButton = page.getByText("Read more");
    if (await readMoreButton.isVisible()) {
      await readMoreButton.click();
      await expect(page.getByText("Show less")).toBeVisible();
    }
  });
});
