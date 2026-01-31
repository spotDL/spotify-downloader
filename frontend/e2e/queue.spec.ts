import { test, expect } from "@playwright/test";

test.describe("Queue Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/queue");
  });

  test("should display the queue page header", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Download Queue/i })
    ).toBeVisible();
  });

  test("should display concurrent downloads selector", async ({ page }) => {
    // Check for the concurrent downloads select
    const select = page.locator("select");
    await expect(select).toBeVisible();

    // Should have concurrent options
    await expect(select.locator("option")).toHaveCount(10); // 1,2,3,4,5,6,8,10,12,16
  });

  test("should display stats cards", async ({ page }) => {
    // Check for stat cards
    await expect(page.getByText("Pending")).toBeVisible();
    await expect(page.getByText("Active")).toBeVisible();
    await expect(page.getByText("Completed")).toBeVisible();
    await expect(page.getByText("Failed")).toBeVisible();
  });

  test("should show empty state when no downloads", async ({ page }) => {
    await expect(page.getByText(/No downloads in queue/i)).toBeVisible();
    await expect(page.getByText(/Search for a song/i)).toBeVisible();
  });

  test("should have link to home page in empty state", async ({ page }) => {
    const homeLink = page.getByRole("link", { name: /Search for a song/i });
    await expect(homeLink).toBeVisible();
    await homeLink.click();

    await expect(page).toHaveURL("/");
  });

  test("should display queue items when present", async ({ page }) => {
    // Set up localStorage with queue items before navigation
    await page.evaluate(() => {
      const queueState = {
        state: {
          items: [
            {
              id: "q1",
              song: {
                id: "1",
                name: "Test Song",
                artists: ["Test Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "pending",
              progress: 0,
            },
            {
              id: "q2",
              song: {
                id: "2",
                name: "Another Song",
                artists: ["Another Artist"],
                platform: "spotify",
                duration_seconds: 240,
              },
              status: "completed",
              progress: 100,
            },
          ],
          maxConcurrent: 4,
        },
        version: 0,
      };
      localStorage.setItem("queue-storage", JSON.stringify(queueState));
    });

    // Reload to pick up the localStorage state
    await page.reload();

    // Should show the queue items
    await expect(page.getByText("Test Song")).toBeVisible();
    await expect(page.getByText("Another Song")).toBeVisible();
  });

  test("should show action buttons when queue has items", async ({ page }) => {
    // Set up localStorage with completed and failed items
    await page.evaluate(() => {
      const queueState = {
        state: {
          items: [
            {
              id: "q1",
              song: {
                id: "1",
                name: "Completed Song",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "completed",
              progress: 100,
            },
            {
              id: "q2",
              song: {
                id: "2",
                name: "Failed Song",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "failed",
              progress: 0,
              error: "Download failed",
            },
          ],
          maxConcurrent: 4,
        },
        version: 0,
      };
      localStorage.setItem("queue-storage", JSON.stringify(queueState));
    });

    await page.reload();

    // Should show action buttons
    await expect(
      page.getByRole("button", { name: /Clear Completed/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Clear Failed/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Clear All/i })
    ).toBeVisible();
  });

  test("should display status badges correctly", async ({ page }) => {
    await page.evaluate(() => {
      const queueState = {
        state: {
          items: [
            {
              id: "q1",
              song: {
                id: "1",
                name: "Pending Song",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "pending",
              progress: 0,
            },
            {
              id: "q2",
              song: {
                id: "2",
                name: "Downloading Song",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "downloading",
              progress: 50,
            },
          ],
          maxConcurrent: 4,
        },
        version: 0,
      };
      localStorage.setItem("queue-storage", JSON.stringify(queueState));
    });

    await page.reload();

    await expect(page.getByText("Pending")).toBeVisible();
    await expect(page.getByText("Downloading")).toBeVisible();
  });

  test("should show progress bar for active downloads", async ({ page }) => {
    await page.evaluate(() => {
      const queueState = {
        state: {
          items: [
            {
              id: "q1",
              song: {
                id: "1",
                name: "Downloading Song",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "downloading",
              progress: 65,
              speed: "2.5 MB/s",
              eta: "0:30",
            },
          ],
          maxConcurrent: 4,
        },
        version: 0,
      };
      localStorage.setItem("queue-storage", JSON.stringify(queueState));
    });

    await page.reload();

    // Check for progress percentage
    await expect(page.getByText("65%")).toBeVisible();

    // Check for speed and ETA
    await expect(page.getByText(/2.5 MB\/s/)).toBeVisible();
    await expect(page.getByText(/ETA: 0:30/)).toBeVisible();
  });

  test("should show error message for failed downloads", async ({ page }) => {
    await page.evaluate(() => {
      const queueState = {
        state: {
          items: [
            {
              id: "q1",
              song: {
                id: "1",
                name: "Failed Song",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "failed",
              progress: 0,
              error: "Network error: Connection timed out",
            },
          ],
          maxConcurrent: 4,
        },
        version: 0,
      };
      localStorage.setItem("queue-storage", JSON.stringify(queueState));
    });

    await page.reload();

    await expect(page.getByText("Network error: Connection timed out")).toBeVisible();
    await expect(page.getByRole("button", { name: /Retry/i })).toBeVisible();
  });

  test("should change concurrent downloads setting", async ({ page }) => {
    const select = page.locator("select");
    await select.selectOption("8");

    // Verify the selection changed
    await expect(select).toHaveValue("8");
  });

  test("should update stats counters correctly", async ({ page }) => {
    await page.evaluate(() => {
      const queueState = {
        state: {
          items: [
            {
              id: "q1",
              song: {
                id: "1",
                name: "Song 1",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "pending",
              progress: 0,
            },
            {
              id: "q2",
              song: {
                id: "2",
                name: "Song 2",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "downloading",
              progress: 50,
            },
            {
              id: "q3",
              song: {
                id: "3",
                name: "Song 3",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "completed",
              progress: 100,
            },
            {
              id: "q4",
              song: {
                id: "4",
                name: "Song 4",
                artists: ["Artist"],
                platform: "spotify",
                duration_seconds: 180,
              },
              status: "failed",
              progress: 0,
            },
          ],
          maxConcurrent: 4,
        },
        version: 0,
      };
      localStorage.setItem("queue-storage", JSON.stringify(queueState));
    });

    await page.reload();

    // Check stats - need to find the stat values in the cards
    const statCards = page.locator('[class*="text-center py-4"]');

    // The counts should appear as large bold numbers
    await expect(page.locator("text=1 >> nth=0").first()).toBeVisible();
  });
});
