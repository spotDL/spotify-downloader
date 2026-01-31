import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "../../src/stores/auth";

describe("Auth Store", () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
    });
    localStorage.clear();
  });

  describe("initial state", () => {
    it("starts with no user", () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it("starts with no access token", () => {
      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
    });

    it("starts not authenticated", () => {
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("setAuth", () => {
    const mockUser = {
      id: "user-123",
      username: "testuser",
      email: "test@example.com",
      reputation_score: 100,
    };
    const mockToken = "jwt-token-abc123";

    it("sets the user", () => {
      useAuthStore.getState().setAuth(mockUser, mockToken);
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });

    it("sets the access token", () => {
      useAuthStore.getState().setAuth(mockUser, mockToken);
      expect(useAuthStore.getState().accessToken).toBe(mockToken);
    });

    it("sets isAuthenticated to true", () => {
      useAuthStore.getState().setAuth(mockUser, mockToken);
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });

    it("stores token in state", () => {
      useAuthStore.getState().setAuth(mockUser, mockToken);
      // The store should have the token
      expect(useAuthStore.getState().accessToken).toBe(mockToken);
    });
  });

  describe("logout", () => {
    const mockUser = {
      id: "user-123",
      username: "testuser",
      email: "test@example.com",
      reputation_score: 100,
    };

    beforeEach(() => {
      // Set up authenticated state
      useAuthStore.getState().setAuth(mockUser, "token");
    });

    it("clears the user", () => {
      useAuthStore.getState().logout();
      expect(useAuthStore.getState().user).toBeNull();
    });

    it("clears the access token", () => {
      useAuthStore.getState().logout();
      expect(useAuthStore.getState().accessToken).toBeNull();
    });

    it("sets isAuthenticated to false", () => {
      useAuthStore.getState().logout();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it("removes token from localStorage", () => {
      useAuthStore.getState().logout();
      expect(localStorage.getItem("access_token")).toBeFalsy();
    });
  });

  describe("auth flow", () => {
    it("handles login and logout cycle", () => {
      const mockUser = {
        id: "user-456",
        username: "cycleuser",
        email: "cycle@example.com",
        reputation_score: 50,
      };

      // Login
      useAuthStore.getState().setAuth(mockUser, "cycle-token");
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user?.username).toBe("cycleuser");

      // Logout
      useAuthStore.getState().logout();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBeNull();
    });

    it("can re-login after logout", () => {
      const user1 = {
        id: "user-1",
        username: "user1",
        email: "user1@example.com",
        reputation_score: 10,
      };
      const user2 = {
        id: "user-2",
        username: "user2",
        email: "user2@example.com",
        reputation_score: 20,
      };

      useAuthStore.getState().setAuth(user1, "token1");
      useAuthStore.getState().logout();
      useAuthStore.getState().setAuth(user2, "token2");

      expect(useAuthStore.getState().user?.username).toBe("user2");
      expect(useAuthStore.getState().accessToken).toBe("token2");
    });
  });
});
