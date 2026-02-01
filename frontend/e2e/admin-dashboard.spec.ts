import { test, expect } from "@playwright/test";

test.describe("Admin Dashboard", () => {
  const mockStats = {
    entities: {
      songs: 150000,
      artists: 25000,
      albums: 35000,
      playlists: 5000,
      matches: 200000,
      users: 1500,
    },
    growth: {
      songs_today: 150,
      songs_this_week: 1200,
      matches_today: 500,
      matches_this_week: 3500,
      downloads_today: 250,
      downloads_this_week: 2000,
      new_users_today: 25,
      new_users_this_week: 180,
    },
    cache: {
      hit_rate: 0.92,
      size_mb: 256.5,
      entries: 50000,
    },
    uptime_seconds: 86400,
  };

  const adminUser = {
    id: "admin-1",
    username: "admin",
    email: "admin@example.com",
    is_active: true,
    is_admin: true,
    reputation_score: 1000,
    created_at: "2024-01-01T00:00:00Z",
  };

  const regularUser = {
    id: "user-1",
    username: "regular",
    email: "regular@example.com",
    is_active: true,
    is_admin: false,
    reputation_score: 100,
    created_at: "2024-06-01T00:00:00Z",
  };

  const setAuthState = async (page: any, user: typeof adminUser) => {
    await page.evaluate((u: typeof adminUser) => {
      const authState = {
        state: {
          user: u,
          accessToken: "test-token",
          isAuthenticated: true,
        },
        version: 0,
      };
      localStorage.setItem("auth-storage", JSON.stringify(authState));
    }, user);
  };

  test.describe("Access Control", () => {
    test("should redirect to login when not authenticated", async ({
      page,
    }) => {
      await page.goto("/admin");

      await expect(page).toHaveURL("/auth/login");
    });

    test("should redirect to home when not admin", async ({ page }) => {
      await page.goto("/admin");
      await setAuthState(page, regularUser);
      await page.reload();

      await expect(page).toHaveURL("/");
    });

    test("should allow access for admin users", async ({ page }) => {
      // Mock stats API
      await page.route("**/api/v1/admin/stats", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });

      await page.goto("/admin");
      await setAuthState(page, adminUser);
      await page.reload();

      await expect(
        page.getByRole("heading", { name: /Admin Dashboard/i })
      ).toBeVisible();
    });
  });

  test.describe("Dashboard Content", () => {
    test.beforeEach(async ({ page }) => {
      // Mock stats API
      await page.route("**/api/v1/admin/stats", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });

      await page.goto("/admin");
      await setAuthState(page, adminUser);
      await page.reload();
    });

    test("should display admin dashboard header", async ({ page }) => {
      await expect(
        page.getByRole("heading", { name: /Admin Dashboard/i })
      ).toBeVisible();
      await expect(
        page.getByText(/Manage users, matches, and system settings/i)
      ).toBeVisible();
    });

    test("should show Admin Only badge", async ({ page }) => {
      await expect(page.getByText("Admin Only")).toBeVisible();
    });

    test("should display quick navigation links", async ({ page }) => {
      await expect(page.getByRole("link", { name: /Users/i })).toBeVisible();
      await expect(page.getByRole("link", { name: /Matches/i })).toBeVisible();
      await expect(page.getByRole("link", { name: /Reports/i })).toBeVisible();
      await expect(
        page.getByRole("link", { name: /Import\/Export/i })
      ).toBeVisible();
    });

    test("should display entity stats", async ({ page }) => {
      await expect(page.getByText("Database Overview")).toBeVisible();
      await expect(page.getByText("150K")).toBeVisible(); // Songs
      await expect(page.getByText("25K")).toBeVisible(); // Artists
      await expect(page.getByText("35K")).toBeVisible(); // Albums
    });

    test("should display growth stats", async ({ page }) => {
      await expect(page.getByText("Today's Activity")).toBeVisible();
      await expect(page.getByText("+150")).toBeVisible(); // Songs today
      await expect(page.getByText("+500")).toBeVisible(); // Matches today
      await expect(page.getByText("+25")).toBeVisible(); // New users today
    });

    test("should display cache stats", async ({ page }) => {
      await expect(page.getByText("Cache Status")).toBeVisible();
      await expect(page.getByText("92.0%")).toBeVisible(); // Hit rate
      await expect(page.getByText("256.5 MB")).toBeVisible(); // Size
      await expect(page.getByText("50K")).toBeVisible(); // Entries
    });

    test("should navigate to Users page", async ({ page }) => {
      await page.route("**/api/v1/admin/users*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            users: [],
            total: 0,
            page: 1,
            per_page: 20,
            total_pages: 0,
          }),
        });
      });

      await page.getByRole("link", { name: "Users" }).first().click();

      await expect(page).toHaveURL("/admin/users");
    });

    test("should navigate to Matches page", async ({ page }) => {
      await page.route("**/api/v1/admin/matches*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            matches: [],
            total: 0,
            page: 1,
            per_page: 20,
          }),
        });
      });

      await page.getByRole("link", { name: "Matches" }).first().click();

      await expect(page).toHaveURL("/admin/matches");
    });

    test("should navigate to Reports page", async ({ page }) => {
      await page.route("**/api/v1/reports*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            reports: [],
            total: 0,
            page: 1,
            page_size: 20,
          }),
        });
      });

      await page.getByRole("link", { name: "Reports" }).first().click();

      await expect(page).toHaveURL("/admin/reports");
    });

    test("should navigate to Import/Export page", async ({ page }) => {
      await page.getByRole("link", { name: "Import/Export" }).click();

      await expect(page).toHaveURL("/admin/import");
    });
  });

  test.describe("Error Handling", () => {
    test("should show error state when stats API fails", async ({ page }) => {
      await page.route("**/api/v1/admin/stats", async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Internal server error" }),
        });
      });

      await page.goto("/admin");
      await setAuthState(page, adminUser);
      await page.reload();

      await expect(page.getByText(/Failed to load dashboard/i)).toBeVisible();
    });

    test("should show loading state while fetching stats", async ({ page }) => {
      await page.route("**/api/v1/admin/stats", async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });

      await page.goto("/admin");
      await setAuthState(page, adminUser);
      await page.reload();

      await expect(page.getByText(/Loading dashboard/i)).toBeVisible();
    });
  });

  test.describe("Admin Users Panel", () => {
    const mockUsers = {
      users: [
        {
          id: "user-1",
          username: "user1",
          email: "user1@example.com",
          is_active: true,
          is_admin: false,
          reputation_score: 100,
          created_at: "2024-01-01T00:00:00Z",
          last_login: "2024-12-01T00:00:00Z",
          matches_submitted: 10,
          votes_cast: 50,
          reports_submitted: 2,
        },
        {
          id: "user-2",
          username: "admin2",
          email: "admin2@example.com",
          is_active: true,
          is_admin: true,
          reputation_score: 500,
          created_at: "2024-01-01T00:00:00Z",
          last_login: "2024-12-15T00:00:00Z",
          matches_submitted: 100,
          votes_cast: 200,
          reports_submitted: 5,
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/v1/admin/stats", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });

      await page.route("**/api/v1/admin/users*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockUsers),
        });
      });

      await page.goto("/admin/users");
      await setAuthState(page, adminUser);
      await page.reload();
    });

    test("should display users list", async ({ page }) => {
      await expect(page.getByText("user1")).toBeVisible();
      await expect(page.getByText("admin2")).toBeVisible();
    });
  });

  test.describe("Admin Matches Panel", () => {
    const mockMatches = {
      matches: [
        {
          id: "match-1",
          source_url: "https://open.spotify.com/track/123",
          target_url: "https://youtube.com/watch?v=abc",
          target_platform: "youtube",
          score: 95,
          confidence: 0.95,
          match_type: "user",
          result: {
            name: "Test Song",
            artists: ["Test Artist"],
            artist: "Test Artist",
            duration: 180,
            platform: "youtube",
            platform_id: "abc",
            url: "https://youtube.com/watch?v=abc",
            album_name: null,
            cover_url: null,
            views: 1000000,
            explicit: false,
            verified: false,
          },
          upvotes: 10,
          downvotes: 2,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    };

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/v1/admin/stats", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });

      await page.route("**/api/v1/admin/matches*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockMatches),
        });
      });

      await page.goto("/admin/matches");
      await setAuthState(page, adminUser);
      await page.reload();
    });

    test("should display matches list", async ({ page }) => {
      await expect(page.getByText("Test Song")).toBeVisible();
      await expect(page.getByText("youtube")).toBeVisible();
    });
  });

  test.describe("Admin Reports Panel", () => {
    const mockReports = {
      reports: [
        {
          id: "report-1",
          entity_type: "song",
          entity_id: "song-123",
          field_name: "name",
          current_value: "Old Name",
          suggested_value: "Correct Name",
          description: "Wrong song name",
          status: "pending",
          reporter_id: "user-1",
          reporter_username: "user1",
          reviewer_id: null,
          reviewed_at: null,
          created_at: "2024-12-01T00:00:00Z",
          updated_at: "2024-12-01T00:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/v1/admin/stats", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });

      await page.route("**/api/v1/reports*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockReports),
        });
      });

      await page.goto("/admin/reports");
      await setAuthState(page, adminUser);
      await page.reload();
    });

    test("should display reports list", async ({ page }) => {
      await expect(page.getByText("Old Name")).toBeVisible();
      await expect(page.getByText("Correct Name")).toBeVisible();
    });
  });
});
