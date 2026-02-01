import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { ToastProvider, useToast } from "../../src/components/ui/toast";

// Mock createPortal to render in the same container
vi.mock("react-dom", async () => {
  const actual = await vi.importActual("react-dom");
  return {
    ...actual,
    createPortal: (node: React.ReactNode) => node,
  };
});

// Test component that uses the toast hook
function TestComponent() {
  const toast = useToast();

  return (
    <div>
      <button onClick={() => toast.success("Success message")}>
        Show Success
      </button>
      <button onClick={() => toast.error("Error message")}>
        Show Error
      </button>
      <button onClick={() => toast.warning("Warning message")}>
        Show Warning
      </button>
      <button onClick={() => toast.info("Info message")}>
        Show Info
      </button>
      <button onClick={() => toast.addToast("Custom", "success", 10000)}>
        Custom Toast
      </button>
    </div>
  );
}

function renderWithProvider(ui?: React.ReactNode) {
  return render(
    <ToastProvider>
      {ui || <TestComponent />}
    </ToastProvider>
  );
}

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("useToast hook", () => {
    it("throws error when used outside ToastProvider", () => {
      // Suppress console error for this test
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      expect(() => {
        const TestOutside = () => {
          useToast();
          return null;
        };
        render(<TestOutside />);
      }).toThrow("useToast must be used within a ToastProvider");

      consoleSpy.mockRestore();
    });

    it("provides toast methods", () => {
      let toastContext: ReturnType<typeof useToast> | null = null;

      function TestAccess() {
        toastContext = useToast();
        return null;
      }

      renderWithProvider(<TestAccess />);

      expect(toastContext).not.toBeNull();
      expect(typeof toastContext!.success).toBe("function");
      expect(typeof toastContext!.error).toBe("function");
      expect(typeof toastContext!.warning).toBe("function");
      expect(typeof toastContext!.info).toBe("function");
      expect(typeof toastContext!.addToast).toBe("function");
      expect(typeof toastContext!.removeToast).toBe("function");
    });
  });

  describe("toast variants", () => {
    it("shows success toast", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));

      expect(screen.getByText("Success message")).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveClass("border-l-[var(--accent-safe)]");
    });

    it("shows error toast", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Error"));

      expect(screen.getByText("Error message")).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveClass("border-l-[var(--accent-peak)]");
    });

    it("shows warning toast", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Warning"));

      expect(screen.getByText("Warning message")).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveClass("border-l-[var(--accent-warm)]");
    });

    it("shows info toast", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Info"));

      expect(screen.getByText("Info message")).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveClass("border-l-[var(--accent-cool)]");
    });
  });

  describe("toast icons", () => {
    it("shows success icon", () => {
      renderWithProvider();
      fireEvent.click(screen.getByText("Show Success"));

      const toast = screen.getByRole("alert");
      const icon = toast.querySelector("svg");
      expect(icon).toBeInTheDocument();
    });

    it("shows error icon", () => {
      renderWithProvider();
      fireEvent.click(screen.getByText("Show Error"));

      const toast = screen.getByRole("alert");
      const icon = toast.querySelector("svg");
      expect(icon).toBeInTheDocument();
    });

    it("shows warning icon", () => {
      renderWithProvider();
      fireEvent.click(screen.getByText("Show Warning"));

      const toast = screen.getByRole("alert");
      const icon = toast.querySelector("svg");
      expect(icon).toBeInTheDocument();
    });

    it("shows info icon", () => {
      renderWithProvider();
      fireEvent.click(screen.getByText("Show Info"));

      const toast = screen.getByRole("alert");
      const icon = toast.querySelector("svg");
      expect(icon).toBeInTheDocument();
    });
  });

  describe("auto-dismiss", () => {
    it("auto-dismisses after default duration (5000ms)", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));
      expect(screen.getByText("Success message")).toBeInTheDocument();

      // Advance past duration
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      // Wait for exit animation (300ms)
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    });

    it("uses custom duration when provided", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Custom Toast"));
      expect(screen.getByText("Custom")).toBeInTheDocument();

      // Should still be visible at 5000ms
      act(() => {
        vi.advanceTimersByTime(5000);
      });
      expect(screen.getByText("Custom")).toBeInTheDocument();

      // Should dismiss after 10000ms + exit animation
      act(() => {
        vi.advanceTimersByTime(5000);
      });
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(screen.queryByText("Custom")).not.toBeInTheDocument();
    });

    it("does not auto-dismiss when duration is 0", async () => {
      function TestPermanent() {
        const toast = useToast();
        return (
          <button onClick={() => toast.addToast("Permanent", "info", 0)}>
            Show Permanent
          </button>
        );
      }

      renderWithProvider(<TestPermanent />);

      fireEvent.click(screen.getByText("Show Permanent"));
      expect(screen.getByText("Permanent")).toBeInTheDocument();

      // Advance a long time
      act(() => {
        vi.advanceTimersByTime(60000);
      });

      // Should still be visible
      expect(screen.getByText("Permanent")).toBeInTheDocument();
    });
  });

  describe("manual dismiss", () => {
    it("dismisses when clicking dismiss button", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));
      expect(screen.getByText("Success message")).toBeInTheDocument();

      const dismissButton = screen.getByLabelText("Dismiss notification");
      fireEvent.click(dismissButton);

      // Wait for exit animation
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    });

    it("dismisses using removeToast", async () => {
      let toastId = "";

      function TestRemove() {
        const toast = useToast();
        return (
          <div>
            <button
              onClick={() => {
                toastId = toast.success("To be removed");
              }}
            >
              Show
            </button>
            <button onClick={() => toast.removeToast(toastId)}>Remove</button>
          </div>
        );
      }

      renderWithProvider(<TestRemove />);

      fireEvent.click(screen.getByText("Show"));
      expect(screen.getByText("To be removed")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Remove"));

      expect(screen.queryByText("To be removed")).not.toBeInTheDocument();
    });
  });

  describe("multiple toasts", () => {
    it("can show multiple toasts", () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));
      fireEvent.click(screen.getByText("Show Error"));
      fireEvent.click(screen.getByText("Show Info"));

      expect(screen.getByText("Success message")).toBeInTheDocument();
      expect(screen.getByText("Error message")).toBeInTheDocument();
      expect(screen.getByText("Info message")).toBeInTheDocument();
    });

    it("dismisses toasts independently", async () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));
      fireEvent.click(screen.getByText("Show Error"));

      // Dismiss only the first toast
      const dismissButtons = screen.getAllByLabelText("Dismiss notification");
      fireEvent.click(dismissButtons[0]);

      act(() => {
        vi.advanceTimersByTime(300);
      });

      // One toast removed, one remains
      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
      expect(screen.getByText("Error message")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has role alert", () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("dismiss button has aria-label", () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));

      expect(screen.getByLabelText("Dismiss notification")).toBeInTheDocument();
    });
  });

  describe("animations", () => {
    it("applies slide-in animation on show", () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));

      expect(screen.getByRole("alert")).toHaveClass("animate-slide-left");
    });

    it("applies fade-out animation on dismiss", () => {
      renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));

      const dismissButton = screen.getByLabelText("Dismiss notification");
      fireEvent.click(dismissButton);

      // During exit animation
      expect(screen.getByRole("alert")).toHaveClass("animate-fade-out");
    });
  });

  describe("toast container", () => {
    it("renders toast container when there are toasts", () => {
      const { container } = renderWithProvider();

      fireEvent.click(screen.getByText("Show Success"));

      const toastContainer = container.querySelector(".toast-container");
      expect(toastContainer).toBeInTheDocument();
    });

    it("does not render toast container when there are no toasts", () => {
      const { container } = renderWithProvider();

      const toastContainer = container.querySelector(".toast-container");
      expect(toastContainer).not.toBeInTheDocument();
    });
  });

  describe("toast ID", () => {
    it("returns unique ID when creating toast", () => {
      const ids: string[] = [];

      function TestIds() {
        const toast = useToast();
        return (
          <button
            onClick={() => {
              ids.push(toast.success("Toast"));
            }}
          >
            Add
          </button>
        );
      }

      renderWithProvider(<TestIds />);

      fireEvent.click(screen.getByText("Add"));
      fireEvent.click(screen.getByText("Add"));
      fireEvent.click(screen.getByText("Add"));

      expect(ids.length).toBe(3);
      expect(new Set(ids).size).toBe(3); // All IDs should be unique
    });
  });
});
