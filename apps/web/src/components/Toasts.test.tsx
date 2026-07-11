import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/errors";

// CONTRACT F/H — `toast.*` is a thin shim over sonner. It maps an ApiError to
// its CONTRACT F copy and routes to the sonner method matching the severity
// (error → error, warn → warning, info → info). The visible <Toaster/> mounts
// once at the app root; here we assert the shim delegates correctly.

const sonnerMock = vi.hoisted(() => ({
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  success: vi.fn(),
  dismiss: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: sonnerMock }));

// Imported after the mock is registered so the shim binds to the mocked toast.
const { toast } = await import("./Toasts");

afterEach(() => {
  vi.clearAllMocks();
});

describe("toast shim", () => {
  it("routes an ApiError to sonner with the CONTRACT F copy at error severity", () => {
    toast.fromApiError(new ApiError("invalid_credentials", "nope", null, 401));
    expect(sonnerMock.error).toHaveBeenCalledWith("Wrong email or password.");
    expect(sonnerMock.warning).not.toHaveBeenCalled();
  });

  it("maps a warn-severity code to a sonner warning", () => {
    toast.fromApiError(new ApiError("email_taken", "taken", null, 409));
    expect(sonnerMock.warning).toHaveBeenCalledWith(
      "An account with that email already exists — sign in instead.",
    );
  });

  it("falls back to a generic message (error severity) for an unknown code", () => {
    // A server ahead of the app sends a code outside the union.
    toast.fromApiError(new ApiError("teapot" as never, "short and stout", null, 418));
    expect(sonnerMock.error).toHaveBeenCalledWith(
      "Server error (teapot): short and stout",
    );
  });

  it("exposes severity helpers that delegate to the matching sonner method", () => {
    toast.info("heads up");
    toast.warn("careful");
    toast.error("boom");
    expect(sonnerMock.info).toHaveBeenCalledWith("heads up");
    expect(sonnerMock.warning).toHaveBeenCalledWith("careful");
    expect(sonnerMock.error).toHaveBeenCalledWith("boom");
  });
});
