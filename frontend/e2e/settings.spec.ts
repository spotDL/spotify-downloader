import { test, expect } from "@playwright/test";

test.describe("Settings Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/settings");
  });

  test("should display the settings page header", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Settings/i })
    ).toBeVisible();
    // Description may include "credentials" in the full version
    await expect(
      page.getByText(/Configure download preferences/i)
    ).toBeVisible();
  });

  test("should display download options section", async ({ page }) => {
    await expect(page.getByText("Download Options")).toBeVisible();
    await expect(
      page.getByText(/Configure audio format, quality, and output settings/i)
    ).toBeVisible();
  });

  test("should have audio format selector with correct options", async ({
    page,
  }) => {
    // Find the Audio Format select
    const formatSelect = page.locator("select").first();
    await expect(formatSelect).toBeVisible();

    // Check options by counting them or selecting them
    await expect(formatSelect.locator("option")).toHaveCount(6);
    // Verify options can be selected
    await formatSelect.selectOption("mp3");
    await expect(formatSelect).toHaveValue("mp3");
    await formatSelect.selectOption("flac");
    await expect(formatSelect).toHaveValue("flac");
  });

  test("should have audio quality selector with correct options", async ({
    page,
  }) => {
    // Find the Audio Quality select (second select on page)
    const qualitySelect = page.locator("select").nth(1);
    await expect(qualitySelect).toBeVisible();

    // Check options by counting them
    await expect(qualitySelect.locator("option")).toHaveCount(5);
    // Verify options can be selected
    await qualitySelect.selectOption("320k");
    await expect(qualitySelect).toHaveValue("320k");
  });

  test("should have output template input", async ({ page }) => {
    const templateInput = page.getByPlaceholder("{artist} - {title}");
    await expect(templateInput).toBeVisible();

    // Check for template hint text
    await expect(page.getByText(/Available:.*\{artist\}/)).toBeVisible();
  });

  test("should have concurrent downloads selector", async ({ page }) => {
    const concurrentSelect = page.locator("select").nth(2);
    await expect(concurrentSelect).toBeVisible();

    // Check options by counting them (1, 2, 3, 4, 5, 6, 8, 10 = 8 options)
    await expect(concurrentSelect.locator("option")).toHaveCount(8);
    // Verify options can be selected
    await concurrentSelect.selectOption("1");
    await expect(concurrentSelect).toHaveValue("1");
    await concurrentSelect.selectOption("10");
    await expect(concurrentSelect).toHaveValue("10");
  });

  test("should have overwrite existing checkbox", async ({ page }) => {
    const checkbox = page.getByRole("checkbox").first();
    await expect(checkbox).toBeVisible();
    await expect(page.getByText("Overwrite existing files")).toBeVisible();
  });

  test("should display metadata embedding section", async ({ page }) => {
    await expect(page.getByText("Metadata Embedding")).toBeVisible();
    await expect(
      page.getByText(/Choose what metadata to embed in downloaded files/i)
    ).toBeVisible();

    // Check for metadata options
    await expect(page.getByText("Embed metadata")).toBeVisible();
    await expect(page.getByText("Embed lyrics")).toBeVisible();
    await expect(page.getByText("Embed cover art")).toBeVisible();
  });

  test("should display server connection section", async ({ page }) => {
    // Wait for the page to fully render
    await page.waitForLoadState("networkidle");

    // Scroll down to make sure server section is in view
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Use specific heading selector to avoid matching the subtitle text
    await expect(page.getByRole("heading", { name: "Server Connection" })).toBeVisible();

    // Check for API URL input
    const apiUrlInput = page.getByPlaceholder("http://localhost:8000");
    await expect(apiUrlInput).toBeVisible();

    // Check for offline mode checkbox
    await expect(page.getByText("Offline mode")).toBeVisible();
  });

  test("should change audio format selection", async ({ page }) => {
    const formatSelect = page.locator("select").first();

    // Change to FLAC
    await formatSelect.selectOption("flac");
    await expect(formatSelect).toHaveValue("flac");

    // Change to OGG
    await formatSelect.selectOption("ogg");
    await expect(formatSelect).toHaveValue("ogg");
  });

  test("should change audio quality selection", async ({ page }) => {
    const qualitySelect = page.locator("select").nth(1);

    // Change to 320k
    await qualitySelect.selectOption("320k");
    await expect(qualitySelect).toHaveValue("320k");
  });

  test("should update output template", async ({ page }) => {
    const templateInput = page.getByPlaceholder("{artist} - {title}");

    await templateInput.clear();
    await templateInput.fill("{artist}/{album}/{title}");

    await expect(templateInput).toHaveValue("{artist}/{album}/{title}");
  });

  test("should toggle checkboxes", async ({ page }) => {
    // Find the overwrite checkbox by its label and click the label (the whole label is clickable)
    const overwriteLabel = page.getByText("Overwrite existing files");
    const overwriteCheckbox = page.locator('label').filter({ hasText: "Overwrite existing files" }).locator('input[type="checkbox"]');

    // Get initial state
    const initialState = await overwriteCheckbox.isChecked();

    // Click on the label text to toggle
    await overwriteLabel.click();

    // Verify it toggled
    await expect(overwriteCheckbox).toBeChecked({ checked: !initialState });
  });

  test("should toggle metadata embedding options", async ({ page }) => {
    // Find the embed metadata checkbox label and click it
    const embedMetadataLabel = page.getByText("Embed metadata").first();
    const embedMetadataCheckbox = page.locator('label').filter({ hasText: "Embed metadata" }).first().locator('input[type="checkbox"]');

    const initialState = await embedMetadataCheckbox.isChecked();
    await embedMetadataLabel.click();
    await expect(embedMetadataCheckbox).toBeChecked({ checked: !initialState });
  });

  test("should update API URL", async ({ page }) => {
    const apiUrlInput = page.getByPlaceholder("http://localhost:8000");

    await apiUrlInput.clear();
    await apiUrlInput.fill("https://api.example.com:3000");

    await expect(apiUrlInput).toHaveValue("https://api.example.com:3000");
  });

  test("should toggle offline mode", async ({ page }) => {
    const offlineModeLabel = page.getByText("Offline mode");
    const offlineModeCheckbox = page.locator('label').filter({ hasText: "Offline mode" }).locator('input[type="checkbox"]');

    const initialState = await offlineModeCheckbox.isChecked();
    await offlineModeLabel.click();
    await expect(offlineModeCheckbox).toBeChecked({ checked: !initialState });
  });

  test("should have reset to defaults button", async ({ page }) => {
    const resetButton = page.getByRole("button", {
      name: /Reset to Defaults/i,
    });
    await expect(resetButton).toBeVisible();
  });

  test("should reset settings to defaults", async ({ page }) => {
    // Change some settings first
    const formatSelect = page.locator("select").first();
    await formatSelect.selectOption("flac");

    const templateInput = page.getByPlaceholder("{artist} - {title}");
    await templateInput.clear();
    await templateInput.fill("{custom}/{template}");

    // Click reset
    const resetButton = page.getByRole("button", {
      name: /Reset to Defaults/i,
    });
    await resetButton.click();

    // Verify settings are reset (default is mp3)
    await expect(formatSelect).toHaveValue("mp3");
  });

  test("should persist settings after reload", async ({ page }) => {
    // Change some settings
    const formatSelect = page.locator("select").first();
    await formatSelect.selectOption("flac");

    const qualitySelect = page.locator("select").nth(1);
    await qualitySelect.selectOption("256k");

    // Reload the page
    await page.reload();

    // Verify settings persisted
    await expect(formatSelect).toHaveValue("flac");
    await expect(qualitySelect).toHaveValue("256k");
  });
});
