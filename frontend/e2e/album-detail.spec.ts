import { test, expect } from "@playwright/test";

test.describe("Album Detail Page", () => {
  const mockAlbum = {
    id: "album-123",
    name: "A Night at the Opera",
    artist_name: "Queen",
    artist_id: "artist-456",
    cover_url: "https://example.com/opera.jpg",
    year: 1975,
    total_tracks: 12,
    platforms: [
      {
        platform: "spotify",
        platform_id: "spotify-album-123",
        url: "https://open.spotify.com/album/spotify-album-123",
      },
    ],
    songs: [
      {
        id: "song-1",
        name: "Death on Two Legs",
        artists: ["Queen"],
        artist: "Queen",
        duration: 225,
        album_name: "A Night at the Opera",
        album_id: "album-123",
        cover_url: "https://example.com/cover1.jpg",
        isrc: "GBUM71029601",
        year: 1975,
        track_number: 1,
        disc_number: 1,
        explicit: true,
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
        name: "Lazing on a Sunday Afternoon",
        artists: ["Queen"],
        artist: "Queen",
        duration: 67,
        album_name: "A Night at the Opera",
        album_id: "album-123",
        cover_url: "https://example.com/cover2.jpg",
        isrc: "GBUM71029602",
        year: 1975,
        track_number: 2,
        disc_number: 1,
        explicit: false,
        platforms: [
          {
            platform: "spotify",
            platform_id: "sp-song-2",
            url: "https://open.spotify.com/track/sp-song-2",
          },
        ],
      },
      {
        id: "song-11",
        name: "Bohemian Rhapsody",
        artists: ["Queen"],
        artist: "Queen",
        duration: 355,
        album_name: "A Night at the Opera",
        album_id: "album-123",
        cover_url: "https://example.com/cover11.jpg",
        isrc: "GBUM71029604",
        year: 1975,
        track_number: 11,
        disc_number: 1,
        explicit: false,
        platforms: [
          {
            platform: "spotify",
            platform_id: "sp-song-11",
            url: "https://open.spotify.com/track/sp-song-11",
          },
        ],
      },
    ],
    album_type: "album",
    release_date: "1975-11-21",
    label: "EMI",
    copyright_text: "(C) 1975 EMI Records Ltd.",
    genres: ["Rock", "Progressive Rock"],
    popularity: 85,
  };

  const mockMultiDiscAlbum = {
    ...mockAlbum,
    id: "album-multi",
    name: "The Wall",
    artist_name: "Pink Floyd",
    total_tracks: 26,
    songs: [
      {
        id: "song-d1-1",
        name: "In the Flesh?",
        artists: ["Pink Floyd"],
        artist: "Pink Floyd",
        duration: 200,
        album_name: "The Wall",
        album_id: "album-multi",
        cover_url: null,
        isrc: null,
        year: 1979,
        track_number: 1,
        disc_number: 1,
        explicit: false,
        platforms: [],
      },
      {
        id: "song-d2-1",
        name: "Hey You",
        artists: ["Pink Floyd"],
        artist: "Pink Floyd",
        duration: 280,
        album_name: "The Wall",
        album_id: "album-multi",
        cover_url: null,
        isrc: null,
        year: 1979,
        track_number: 1,
        disc_number: 2,
        explicit: false,
        platforms: [],
      },
    ],
  };

  test.beforeEach(async ({ page }) => {
    // Mock the album API
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockAlbum),
      });
    });
  });

  test("should display album name and cover", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(
      page.getByRole("heading", { name: "A Night at the Opera", level: 1 })
    ).toBeVisible();
  });

  test("should display album type badge", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Album")).toBeVisible();
  });

  test("should display artist name with link", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Queen")).toBeVisible();
  });

  test("should navigate to artist page when clicking artist", async ({
    page,
  }) => {
    await page.goto("/album/album-123");

    await page.getByRole("link", { name: "Queen" }).click();

    await expect(page).toHaveURL(/\/artist\/artist-456/);
  });

  test("should display release date", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("November 21, 1975")).toBeVisible();
  });

  test("should display track count", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("12 tracks")).toBeVisible();
  });

  test("should display total duration", async ({ page }) => {
    await page.goto("/album/album-123");

    // Total of songs in mock: 225 + 67 + 355 = 647 seconds = 10 min
    await expect(page.getByText(/min/)).toBeVisible();
  });

  test("should display genres", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Rock")).toBeVisible();
    await expect(page.getByText("Progressive Rock")).toBeVisible();
  });

  test("should display record label", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText(/EMI/)).toBeVisible();
  });

  test("should display platform links", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Listen On")).toBeVisible();
  });

  test("should display track list", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Tracks")).toBeVisible();
    await expect(page.getByText("Death on Two Legs")).toBeVisible();
    await expect(
      page.getByText("Lazing on a Sunday Afternoon")
    ).toBeVisible();
    await expect(page.getByText("Bohemian Rhapsody")).toBeVisible();
  });

  test("should display track numbers", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("01")).toBeVisible();
    await expect(page.getByText("02")).toBeVisible();
    await expect(page.getByText("11")).toBeVisible();
  });

  test("should display track durations", async ({ page }) => {
    await page.goto("/album/album-123");

    // Death on Two Legs is 225 seconds = 3:45
    await expect(page.getByText("3:45")).toBeVisible();
    // Lazing is 67 seconds = 1:07
    await expect(page.getByText("1:07")).toBeVisible();
    // Bohemian Rhapsody is 355 seconds = 5:55
    await expect(page.getByText("5:55")).toBeVisible();
  });

  test("should show explicit badge for explicit tracks", async ({ page }) => {
    await page.goto("/album/album-123");

    // Death on Two Legs is explicit
    await expect(page.getByText("E")).toBeVisible();
  });

  test("should navigate to song page when clicking track", async ({ page }) => {
    await page.goto("/album/album-123");

    await page.getByRole("link", { name: "Bohemian Rhapsody" }).click();

    await expect(page).toHaveURL(/\/song\/song-11/);
  });

  test("should have Download Album button", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(
      page.getByRole("button", { name: /Download Album/i })
    ).toBeVisible();
  });

  test("should have Show/Hide Details button", async ({ page }) => {
    await page.goto("/album/album-123");

    const detailsButton = page.getByRole("button", { name: /Details/i });
    await expect(detailsButton).toBeVisible();
  });

  test("should toggle album details visibility", async ({ page }) => {
    await page.goto("/album/album-123");

    // Details should be visible by default
    await expect(page.getByText("Album Details")).toBeVisible();

    // Click to hide
    await page.getByRole("button", { name: /Hide Details/i }).click();

    // Should not be visible
    await expect(page.getByText("Album Details")).not.toBeVisible();

    // Click to show again
    await page.getByRole("button", { name: /Show Details/i }).click();

    // Should be visible again
    await expect(page.getByText("Album Details")).toBeVisible();
  });

  test("should show Report Issue button when authenticated", async ({
    page,
  }) => {
    await page.goto("/album/album-123");

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

  test("should display copyright info", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Rights Information")).toBeVisible();
    await expect(page.getByText("(C) 1975 EMI Records Ltd.")).toBeVisible();
  });

  test("should display quick stats card", async ({ page }) => {
    await page.goto("/album/album-123");

    await expect(page.getByText("Tracks", { exact: true })).toBeVisible();
    await expect(page.getByText("Duration")).toBeVisible();
  });

  test("should display disc headers for multi-disc albums", async ({
    page,
  }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockMultiDiscAlbum),
      });
    });

    await page.goto("/album/album-multi");

    await expect(page.getByText("Disc 1")).toBeVisible();
    await expect(page.getByText("Disc 2")).toBeVisible();
    await expect(page.getByText("2 discs")).toBeVisible();
  });

  test("should show loading state initially", async ({ page }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockAlbum),
      });
    });

    await page.goto("/album/album-123");

    await expect(page.getByText(/Loading album/i)).toBeVisible();
  });

  test("should show error state on API failure", async ({ page }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.goto("/album/album-error");

    await expect(page.getByText(/Failed to load album/i)).toBeVisible();
  });

  test("should show not found state for missing album", async ({ page }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Album not found" }),
      });
    });

    await page.goto("/album/album-notfound");

    await expect(page.getByText(/Album not found/i)).toBeVisible();
  });

  test("should display single album type info card", async ({ page }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...mockAlbum,
          album_type: "single",
          total_tracks: 1,
        }),
      });
    });

    await page.goto("/album/album-single");

    await expect(page.getByText("Single")).toBeVisible();
    await expect(page.getByText("Single Release")).toBeVisible();
  });

  test("should display EP album type info card", async ({ page }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...mockAlbum,
          album_type: "ep",
          total_tracks: 5,
        }),
      });
    });

    await page.goto("/album/album-ep");

    await expect(page.getByText("EP")).toBeVisible();
    await expect(page.getByText("Extended Play")).toBeVisible();
  });

  test("should display compilation album type info card", async ({ page }) => {
    await page.route("**/api/v1/entities/albums/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...mockAlbum,
          album_type: "compilation",
          total_tracks: 20,
        }),
      });
    });

    await page.goto("/album/album-comp");

    await expect(page.getByText("Compilation")).toBeVisible();
    await expect(page.getByText("Compilation Album")).toBeVisible();
  });

  test("should show popularity badge for popular albums", async ({ page }) => {
    await page.goto("/album/album-123");

    // Album has popularity 85, which should show Popular badge
    await expect(page.getByText("Popular")).toBeVisible();
  });
});
