import { afterEach, describe, expect, it } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { Toasts, toast } from "./Toasts";
import { ApiError } from "../api/errors";

// CONTRACT F/H — the toast system renders an ApiError with the mapped copy and
// its severity.

afterEach(() => {
  // The toast queue is a module-global store — drain it between cases.
  act(() => toast.clear());
});

describe("Toasts", () => {
  it("renders an ApiError with the CONTRACT F copy and error severity", () => {
    render(<Toasts />);
    act(() => {
      toast.fromApiError(
        new ApiError("invalid_credentials", "nope", null, 401),
      );
    });
    const row = screen.getByText("Wrong email or password.").closest("[data-severity]");
    expect(row).not.toBeNull();
    expect(row).toHaveAttribute("data-severity", "error");
  });

  it("maps a warn-severity code to a warn toast", () => {
    render(<Toasts />);
    act(() => {
      toast.fromApiError(new ApiError("email_taken", "taken", null, 409));
    });
    const row = screen
      .getByText("An account with that email already exists — sign in instead.")
      .closest("[data-severity]");
    expect(row).toHaveAttribute("data-severity", "warn");
  });

  it("falls back to a generic message for an unknown code", () => {
    render(<Toasts />);
    act(() => {
      // A server ahead of the app sends a code outside the union.
      toast.fromApiError(
        new ApiError("teapot" as never, "short and stout", null, 418),
      );
    });
    expect(
      screen.getByText("Server error (teapot): short and stout"),
    ).toBeInTheDocument();
  });
});
