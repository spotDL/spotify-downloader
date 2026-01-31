import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.describe("Login Page", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/auth/login");
    });

    test("should display the login form", async ({ page }) => {
      await expect(
        page.getByRole("heading", { name: /Welcome Back/i })
      ).toBeVisible();

      await expect(page.getByPlaceholder(/Enter your username/i)).toBeVisible();
      await expect(page.getByPlaceholder(/Enter your password/i)).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Sign In/i })
      ).toBeVisible();
    });

    test("should have link to register page", async ({ page }) => {
      await expect(page.getByText(/Don't have an account\?/i)).toBeVisible();

      const createAccountLink = page.getByRole("link", { name: /Create one/i });
      await expect(createAccountLink).toBeVisible();

      await createAccountLink.click();
      await expect(page).toHaveURL("/auth/register");
    });

    test("should show validation for required fields", async ({ page }) => {
      const usernameInput = page.getByPlaceholder(/Enter your username/i);
      const passwordInput = page.getByPlaceholder(/Enter your password/i);

      // Inputs should be required
      await expect(usernameInput).toHaveAttribute("required", "");
      await expect(passwordInput).toHaveAttribute("required", "");
    });

    test("should allow entering credentials", async ({ page }) => {
      const usernameInput = page.getByPlaceholder(/Enter your username/i);
      const passwordInput = page.getByPlaceholder(/Enter your password/i);

      await usernameInput.fill("testuser");
      await passwordInput.fill("testpassword123");

      await expect(usernameInput).toHaveValue("testuser");
      await expect(passwordInput).toHaveValue("testpassword123");
    });

    test("should show loading state during login", async ({ page }) => {
      // Mock slow API response
      await page.route("**/api/v1/auth/login", async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            access_token: "test-token",
            user: { id: "1", username: "testuser", email: "test@example.com" },
          }),
        });
      });

      await page.getByPlaceholder(/Enter your username/i).fill("testuser");
      await page
        .getByPlaceholder(/Enter your password/i)
        .fill("testpassword123");
      await page.getByRole("button", { name: /Sign In/i }).click();

      // Button should show loading state
      const submitButton = page.getByRole("button", { name: /Sign In/i });
      // Check for loading indicator (button disabled or spinner)
      await expect(submitButton).toBeDisabled();
    });

    test("should handle successful login", async ({ page }) => {
      // Mock successful login
      await page.route("**/api/v1/auth/login", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            access_token: "test-access-token",
            user: {
              id: "1",
              username: "testuser",
              email: "test@example.com",
            },
          }),
        });
      });

      await page.getByPlaceholder(/Enter your username/i).fill("testuser");
      await page
        .getByPlaceholder(/Enter your password/i)
        .fill("testpassword123");
      await page.getByRole("button", { name: /Sign In/i }).click();

      // Should redirect to home page
      await expect(page).toHaveURL("/");
    });

    test("should display error message on failed login", async ({ page }) => {
      // Mock failed login
      await page.route("**/api/v1/auth/login", async (route) => {
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Invalid credentials" }),
        });
      });

      await page.getByPlaceholder(/Enter your username/i).fill("wronguser");
      await page.getByPlaceholder(/Enter your password/i).fill("wrongpassword");
      await page.getByRole("button", { name: /Sign In/i }).click();

      // Should show error message
      await expect(page.locator(".text-red-400")).toBeVisible();
    });

    test("password field should hide input", async ({ page }) => {
      const passwordInput = page.getByPlaceholder(/Enter your password/i);
      await expect(passwordInput).toHaveAttribute("type", "password");
    });
  });

  test.describe("Register Page", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/auth/register");
    });

    test("should display the registration form", async ({ page }) => {
      await expect(
        page.getByRole("heading", { name: /Create Account/i })
      ).toBeVisible();

      await expect(
        page.getByPlaceholder(/Choose a username/i)
      ).toBeVisible();
      await expect(page.getByPlaceholder(/Enter your email/i)).toBeVisible();
      await expect(page.getByPlaceholder(/Create a password/i)).toBeVisible();
      await expect(
        page.getByPlaceholder(/Confirm your password/i)
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Create Account/i })
      ).toBeVisible();
    });

    test("should have link to login page", async ({ page }) => {
      await expect(page.getByText(/Already have an account\?/i)).toBeVisible();

      const signInLink = page.getByRole("link", { name: /Sign in/i });
      await expect(signInLink).toBeVisible();

      await signInLink.click();
      await expect(page).toHaveURL("/auth/login");
    });

    test("should validate all fields are required", async ({ page }) => {
      const usernameInput = page.getByPlaceholder(/Choose a username/i);
      const emailInput = page.getByPlaceholder(/Enter your email/i);
      const passwordInput = page.getByPlaceholder(/Create a password/i);
      const confirmPasswordInput = page.getByPlaceholder(
        /Confirm your password/i
      );

      await expect(usernameInput).toHaveAttribute("required", "");
      await expect(emailInput).toHaveAttribute("required", "");
      await expect(passwordInput).toHaveAttribute("required", "");
      await expect(confirmPasswordInput).toHaveAttribute("required", "");
    });

    test("should validate email format", async ({ page }) => {
      const emailInput = page.getByPlaceholder(/Enter your email/i);
      await expect(emailInput).toHaveAttribute("type", "email");
    });

    test("should show error for password mismatch", async ({ page }) => {
      await page.getByPlaceholder(/Choose a username/i).fill("testuser");
      await page.getByPlaceholder(/Enter your email/i).fill("test@example.com");
      await page.getByPlaceholder(/Create a password/i).fill("password123");
      await page
        .getByPlaceholder(/Confirm your password/i)
        .fill("differentpassword");

      await page.getByRole("button", { name: /Create Account/i }).click();

      // Should show password mismatch error
      await expect(page.getByText(/Passwords do not match/i)).toBeVisible();
    });

    test("should show error for password too short", async ({ page }) => {
      await page.getByPlaceholder(/Choose a username/i).fill("testuser");
      await page.getByPlaceholder(/Enter your email/i).fill("test@example.com");
      await page.getByPlaceholder(/Create a password/i).fill("short");
      await page.getByPlaceholder(/Confirm your password/i).fill("short");

      await page.getByRole("button", { name: /Create Account/i }).click();

      // Should show password length error
      await expect(
        page.getByText(/Password must be at least 8 characters/i)
      ).toBeVisible();
    });

    test("should handle successful registration", async ({ page }) => {
      // Mock successful registration
      await page.route("**/api/v1/auth/register", async (route) => {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            access_token: "test-access-token",
            user: {
              id: "1",
              username: "newuser",
              email: "new@example.com",
            },
          }),
        });
      });

      await page.getByPlaceholder(/Choose a username/i).fill("newuser");
      await page.getByPlaceholder(/Enter your email/i).fill("new@example.com");
      await page.getByPlaceholder(/Create a password/i).fill("password123");
      await page.getByPlaceholder(/Confirm your password/i).fill("password123");

      await page.getByRole("button", { name: /Create Account/i }).click();

      // Should redirect to home page
      await expect(page).toHaveURL("/");
    });

    test("should display error on registration failure", async ({ page }) => {
      // Mock registration failure
      await page.route("**/api/v1/auth/register", async (route) => {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Username already exists" }),
        });
      });

      await page.getByPlaceholder(/Choose a username/i).fill("existinguser");
      await page
        .getByPlaceholder(/Enter your email/i)
        .fill("existing@example.com");
      await page.getByPlaceholder(/Create a password/i).fill("password123");
      await page.getByPlaceholder(/Confirm your password/i).fill("password123");

      await page.getByRole("button", { name: /Create Account/i }).click();

      // Should show error message
      await expect(page.locator(".text-red-400")).toBeVisible();
    });
  });

  test.describe("Navigation Authentication State", () => {
    test("should show login and signup buttons when not authenticated", async ({
      page,
    }) => {
      await page.goto("/");

      await expect(
        page.getByRole("button", { name: /Login/i })
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Sign Up/i })
      ).toBeVisible();
    });

    test("should show user info and logout when authenticated", async ({
      page,
    }) => {
      // Set up authenticated state
      await page.goto("/");

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

      // Should show username and logout button
      await expect(page.getByText("testuser")).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Logout/i })
      ).toBeVisible();

      // Should not show login/signup buttons
      await expect(
        page.getByRole("link", { name: /Login/i })
      ).not.toBeVisible();
      await expect(
        page.getByRole("link", { name: /Sign Up/i })
      ).not.toBeVisible();
    });

    test("should handle logout", async ({ page }) => {
      // Set up authenticated state
      await page.goto("/");

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

      // Mock logout endpoint
      await page.route("**/api/v1/auth/logout", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      });

      await page.reload();

      // Click logout
      await page.getByRole("button", { name: /Logout/i }).click();

      // Should show login/signup buttons again
      await expect(
        page.getByRole("button", { name: /Login/i })
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Sign Up/i })
      ).toBeVisible();
    });

    test("should navigate to login from navbar", async ({ page }) => {
      await page.goto("/");

      const loginButton = page.locator("nav").getByRole("button", { name: /Login/i });
      await loginButton.click();

      await expect(page).toHaveURL("/auth/login");
    });

    test("should navigate to register from navbar", async ({ page }) => {
      await page.goto("/");

      const signUpButton = page.locator("nav").getByRole("button", { name: /Sign Up/i });
      await signUpButton.click();

      await expect(page).toHaveURL("/auth/register");
    });
  });
});
