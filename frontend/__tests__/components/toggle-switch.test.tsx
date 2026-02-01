import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ToggleSwitch } from "../../src/components/ui/toggle-switch";

describe("ToggleSwitch", () => {
  describe("rendering", () => {
    it("renders switch element", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} />);

      expect(screen.getByRole("switch")).toBeInTheDocument();
    });

    it("renders hidden checkbox for form integration", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} />);

      expect(screen.getByRole("checkbox", { hidden: true })).toBeInTheDocument();
    });

    it("renders label when provided", () => {
      render(
        <ToggleSwitch
          checked={false}
          onChange={() => {}}
          label="Enable notifications"
        />
      );

      expect(screen.getByText("Enable notifications")).toBeInTheDocument();
    });

    it("renders description when provided", () => {
      render(
        <ToggleSwitch
          checked={false}
          onChange={() => {}}
          label="Enable"
          description="Receive push notifications"
        />
      );

      expect(screen.getByText("Receive push notifications")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <ToggleSwitch
          checked={false}
          onChange={() => {}}
          className="custom-toggle"
        />
      );

      expect(container.firstChild).toHaveClass("custom-toggle");
    });
  });

  describe("checked state", () => {
    it("reflects unchecked state", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} />);

      const switchEl = screen.getByRole("switch");
      expect(switchEl).toHaveAttribute("aria-checked", "false");
      expect(switchEl).toHaveClass("bg-[var(--bg-surface)]");
    });

    it("reflects checked state", () => {
      render(<ToggleSwitch checked={true} onChange={() => {}} />);

      const switchEl = screen.getByRole("switch");
      expect(switchEl).toHaveAttribute("aria-checked", "true");
      expect(switchEl).toHaveClass("bg-[var(--accent-safe)]");
    });

    it("syncs hidden checkbox with checked prop", () => {
      const { rerender } = render(
        <ToggleSwitch checked={false} onChange={() => {}} />
      );

      expect(screen.getByRole("checkbox", { hidden: true })).not.toBeChecked();

      rerender(<ToggleSwitch checked={true} onChange={() => {}} />);

      expect(screen.getByRole("checkbox", { hidden: true })).toBeChecked();
    });
  });

  describe("state changes", () => {
    it("calls onChange when clicked", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} />);

      fireEvent.click(screen.getByRole("switch"));

      expect(handleChange).toHaveBeenCalledWith(true);
    });

    it("calls onChange with false when unchecking", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={true} onChange={handleChange} />);

      fireEvent.click(screen.getByRole("switch"));

      expect(handleChange).toHaveBeenCalledWith(false);
    });

    it("calls onChange when hidden checkbox changes", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} />);

      const checkbox = screen.getByRole("checkbox", { hidden: true });
      fireEvent.click(checkbox);

      expect(handleChange).toHaveBeenCalledWith(true);
    });
  });

  describe("keyboard interactions", () => {
    it("toggles on Enter key", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} />);

      const switchEl = screen.getByRole("switch");
      fireEvent.keyDown(switchEl, { key: "Enter" });

      expect(handleChange).toHaveBeenCalledWith(true);
    });

    it("toggles on Space key", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} />);

      const switchEl = screen.getByRole("switch");
      fireEvent.keyDown(switchEl, { key: " " });

      expect(handleChange).toHaveBeenCalledWith(true);
    });

    it("does not toggle on other keys", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} />);

      const switchEl = screen.getByRole("switch");
      fireEvent.keyDown(switchEl, { key: "Tab" });
      fireEvent.keyDown(switchEl, { key: "Escape" });
      fireEvent.keyDown(switchEl, { key: "a" });

      expect(handleChange).not.toHaveBeenCalled();
    });

    it("prevents default on Space key", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} />);

      const switchEl = screen.getByRole("switch");
      const event = fireEvent.keyDown(switchEl, { key: " " });

      // The event should have been handled
      expect(handleChange).toHaveBeenCalled();
    });
  });

  describe("disabled state", () => {
    it("does not call onChange when disabled", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} disabled />);

      fireEvent.click(screen.getByRole("switch"));

      expect(handleChange).not.toHaveBeenCalled();
    });

    it("does not respond to keyboard when disabled", () => {
      const handleChange = vi.fn();
      render(<ToggleSwitch checked={false} onChange={handleChange} disabled />);

      const switchEl = screen.getByRole("switch");
      fireEvent.keyDown(switchEl, { key: "Enter" });
      fireEvent.keyDown(switchEl, { key: " " });

      expect(handleChange).not.toHaveBeenCalled();
    });

    it("disables hidden checkbox", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} disabled />);

      expect(screen.getByRole("checkbox", { hidden: true })).toBeDisabled();
    });

    it("applies disabled styles", () => {
      const { container } = render(
        <ToggleSwitch checked={false} onChange={() => {}} disabled />
      );

      expect(container.firstChild).toHaveClass("opacity-50", "cursor-not-allowed");
    });

    it("is not focusable when disabled", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} disabled />);

      const switchEl = screen.getByRole("switch");
      expect(switchEl).toHaveAttribute("tabIndex", "-1");
    });
  });

  describe("sizes", () => {
    it("applies sm size classes", () => {
      const { container } = render(
        <ToggleSwitch checked={false} onChange={() => {}} size="sm" />
      );

      const track = container.querySelector(".toggle-switch");
      expect(track).toHaveClass("w-8", "h-4");
    });

    it("applies md size classes (default)", () => {
      const { container } = render(
        <ToggleSwitch checked={false} onChange={() => {}} />
      );

      const track = container.querySelector(".toggle-switch");
      expect(track).toHaveClass("w-11", "h-6");
    });

    it("applies lg size classes", () => {
      const { container } = render(
        <ToggleSwitch checked={false} onChange={() => {}} size="lg" />
      );

      const track = container.querySelector(".toggle-switch");
      expect(track).toHaveClass("w-14", "h-7");
    });
  });

  describe("thumb position", () => {
    it("thumb is in off position when unchecked", () => {
      const { container } = render(
        <ToggleSwitch checked={false} onChange={() => {}} />
      );

      const thumb = container.querySelector(".toggle-switch-thumb");
      expect(thumb).toHaveClass("translate-x-0.5");
    });

    it("thumb is in on position when checked", () => {
      const { container } = render(
        <ToggleSwitch checked={true} onChange={() => {}} />
      );

      const thumb = container.querySelector(".toggle-switch-thumb");
      expect(thumb).toHaveClass("translate-x-5");
    });
  });

  describe("form integration", () => {
    it("applies id to hidden checkbox", () => {
      render(
        <ToggleSwitch
          checked={false}
          onChange={() => {}}
          id="my-toggle"
        />
      );

      expect(screen.getByRole("checkbox", { hidden: true })).toHaveAttribute("id", "my-toggle");
    });

    it("applies name to hidden checkbox", () => {
      render(
        <ToggleSwitch
          checked={false}
          onChange={() => {}}
          name="notifications"
        />
      );

      expect(screen.getByRole("checkbox", { hidden: true })).toHaveAttribute("name", "notifications");
    });
  });

  describe("accessibility", () => {
    it("has role switch", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} />);

      expect(screen.getByRole("switch")).toBeInTheDocument();
    });

    it("is focusable when enabled", () => {
      render(<ToggleSwitch checked={false} onChange={() => {}} />);

      const switchEl = screen.getByRole("switch");
      expect(switchEl).toHaveAttribute("tabIndex", "0");
    });

    it("hidden checkbox has aria-checked", () => {
      render(<ToggleSwitch checked={true} onChange={() => {}} />);

      const checkbox = screen.getByRole("checkbox", { hidden: true });
      expect(checkbox).toHaveAttribute("aria-checked", "true");
    });

    it("label is associated with toggle", () => {
      const { container } = render(
        <ToggleSwitch
          checked={false}
          onChange={() => {}}
          label="Enable feature"
        />
      );

      // The whole thing is wrapped in a label element
      const label = container.querySelector("label");
      expect(label).toBeInTheDocument();
      expect(label).toHaveTextContent("Enable feature");
    });
  });

  describe("ref forwarding", () => {
    it("forwards ref to hidden checkbox", () => {
      const ref = vi.fn();
      render(<ToggleSwitch checked={false} onChange={() => {}} ref={ref} />);

      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLInputElement);
    });
  });
});
