import axios, { AxiosError } from "axios";
import { config } from "@/config";
import { forceLogout } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";

export function resolveApiBaseUrl(apiUrl: string | undefined): string {
  const trimmed = (apiUrl || "").trim();
  if (!trimmed) {
    return "/api/v1";
  }

  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return `${trimmed.replace(/\/+$/, "")}/api/v1`;
  }

  const normalized = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return `${normalized.replace(/\/+$/, "")}/api/v1`;
}

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(config.apiUrl),
  headers: {
    "Content-Type": "application/json",
  },
});

const initialApiUrl = useSettingsStore.getState().apiUrl || config.apiUrl;
apiClient.defaults.baseURL = resolveApiBaseUrl(initialApiUrl);

useSettingsStore.subscribe((state, prev) => {
  if (state.apiUrl !== prev.apiUrl) {
    apiClient.defaults.baseURL = resolveApiBaseUrl(state.apiUrl);
  }
});

/**
 * Check if a JWT token is expired by decoding the payload.
 * Returns true if expired or invalid, false if still valid.
 */
function isTokenExpired(token: string): boolean {
  try {
    // JWT format: header.payload.signature
    const parts = token.split(".");
    if (parts.length !== 3) return true;

    // Decode the payload (base64url)
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));

    // Check expiration (exp is in seconds, Date.now() is in milliseconds)
    if (!payload.exp) return false; // No expiration = assume valid

    // Add 10 second buffer to account for clock skew
    return payload.exp * 1000 < Date.now() + 10000;
  } catch {
    // If we can't decode, assume expired/invalid
    return true;
  }
}

/**
 * Extract a user-friendly error message from an API error response.
 * The backend typically returns errors in the format:
 * - { detail: "message" } for FastAPI HTTPException
 * - { detail: [{ msg: "message", loc: [...] }] } for validation errors
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError && error.response?.data) {
    const data = error.response.data;

    // Handle FastAPI validation errors (array of errors)
    if (Array.isArray(data.detail)) {
      const messages = data.detail.map((err: { msg: string; loc?: string[] }) => {
        const field = err.loc?.slice(-1)[0];
        return field ? `${field}: ${err.msg}` : err.msg;
      });
      return messages.join(". ");
    }

    // Handle simple string detail
    if (typeof data.detail === "string") {
      return data.detail;
    }

    // Handle message field
    if (typeof data.message === "string") {
      return data.message;
    }

    // Handle error field
    if (typeof data.error === "string") {
      return data.error;
    }
  }

  // Provide user-friendly messages for common HTTP errors
  if (error instanceof AxiosError) {
    switch (error.response?.status) {
      case 400:
        return "Invalid request. Please check your input.";
      case 401:
        return "Invalid credentials. Please try again.";
      case 403:
        return "You don't have permission to perform this action.";
      case 404:
        return "The requested resource was not found.";
      case 409:
        return "This resource already exists.";
      case 422:
        return "Invalid data provided. Please check your input.";
      case 429:
        return "Too many requests. Please wait a moment.";
      case 500:
        return "Server error. Please try again later.";
      case 502:
      case 503:
      case 504:
        return "Service temporarily unavailable. Please try again later.";
    }
  }

  // Fallback to error message or generic message
  if (error instanceof Error) {
    return error.message;
  }

  return "An unexpected error occurred. Please try again.";
}

/**
 * Create an Error with a user-friendly message extracted from the API response.
 */
function createUserFriendlyError(error: AxiosError): Error {
  const message = getErrorMessage(error);
  const userError = new Error(message);
  // Preserve original error for debugging
  (userError as Error & { cause?: unknown }).cause = error;
  return userError;
}

// Add auth token to requests if available, and check expiration
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    // Check if token is expired before making the request
    if (isTokenExpired(token)) {
      // Token expired - force logout and don't add the token
      forceLogout();
      // Still allow the request to proceed (will fail with 401, but that's expected)
    } else {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle errors and transform to user-friendly messages
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Force logout on 401 (but not for login/register endpoints)
    if (error.response?.status === 401) {
      const url = error.config?.url || "";
      const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/register");
      if (!isAuthEndpoint) {
        // Clear auth state completely - token expired or invalid
        forceLogout();
      }
    }

    // Transform to user-friendly error
    return Promise.reject(createUserFriendlyError(error));
  }
);
