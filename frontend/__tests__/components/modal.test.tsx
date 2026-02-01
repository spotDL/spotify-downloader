import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Modal, ConfirmModal } from "../../src/components/ui/modal";

// Mock createPortal to render in the same container
vi.mock("react-dom", async () => {
  const actual = await vi.importActual("react-dom");
  return {
    ...actual,
    createPortal: (node: React.ReactNode) => node,
  };
});

describe("Modal", () => {
  describe("rendering", () => {
    it("renders when isOpen is true", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Modal Content</p>
        </Modal>
      );

      expect(screen.getByText("Modal Content")).toBeInTheDocument();
    });

    it("does not render when isOpen is false", () => {
      render(
        <Modal isOpen={false} onClose={() => {}}>
          <p>Modal Content</p>
        </Modal>
      );

      expect(screen.queryByText("Modal Content")).not.toBeInTheDocument();
    });

    it("renders title when provided", () => {
      render(
        <Modal isOpen onClose={() => {}} title="Test Modal">
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByText("Test Modal")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Test Modal" })).toBeInTheDocument();
    });

    it("renders description when provided", () => {
      render(
        <Modal
          isOpen
          onClose={() => {}}
          title="Title"
          description="This is a description"
        >
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByText("This is a description")).toBeInTheDocument();
    });

    it("renders footer when provided", () => {
      render(
        <Modal
          isOpen
          onClose={() => {}}
          footer={<button>Submit</button>}
        >
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <Modal isOpen onClose={() => {}} className="custom-modal">
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveClass("custom-modal");
    });
  });

  describe("sizes", () => {
    it("applies sm size class", () => {
      render(
        <Modal isOpen onClose={() => {}} size="sm">
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveClass("max-w-sm");
    });

    it("applies md size class (default)", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveClass("max-w-md");
    });

    it("applies lg size class", () => {
      render(
        <Modal isOpen onClose={() => {}} size="lg">
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveClass("max-w-lg");
    });

    it("applies xl size class", () => {
      render(
        <Modal isOpen onClose={() => {}} size="xl">
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveClass("max-w-xl");
    });

    it("applies full size class", () => {
      render(
        <Modal isOpen onClose={() => {}} size="full">
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveClass("max-w-4xl");
    });
  });

  describe("close button", () => {
    it("shows close button by default", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByLabelText("Close modal")).toBeInTheDocument();
    });

    it("hides close button when showCloseButton is false", () => {
      render(
        <Modal isOpen onClose={() => {}} showCloseButton={false}>
          <p>Content</p>
        </Modal>
      );

      expect(screen.queryByLabelText("Close modal")).not.toBeInTheDocument();
    });

    it("calls onClose when close button is clicked", () => {
      const handleClose = vi.fn();
      render(
        <Modal isOpen onClose={handleClose}>
          <p>Content</p>
        </Modal>
      );

      fireEvent.click(screen.getByLabelText("Close modal"));
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("backdrop click", () => {
    it("closes modal on backdrop click by default", () => {
      const handleClose = vi.fn();
      render(
        <Modal isOpen onClose={handleClose}>
          <p>Content</p>
        </Modal>
      );

      const backdrop = screen.getByRole("dialog");
      fireEvent.click(backdrop);
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it("does not close modal on backdrop click when closeOnBackdropClick is false", () => {
      const handleClose = vi.fn();
      render(
        <Modal isOpen onClose={handleClose} closeOnBackdropClick={false}>
          <p>Content</p>
        </Modal>
      );

      const backdrop = screen.getByRole("dialog");
      fireEvent.click(backdrop);
      expect(handleClose).not.toHaveBeenCalled();
    });

    it("does not close when clicking modal content", () => {
      const handleClose = vi.fn();
      render(
        <Modal isOpen onClose={handleClose}>
          <p>Content</p>
        </Modal>
      );

      fireEvent.click(screen.getByText("Content"));
      expect(handleClose).not.toHaveBeenCalled();
    });
  });

  describe("keyboard interactions", () => {
    it("closes modal on Escape key by default", () => {
      const handleClose = vi.fn();
      render(
        <Modal isOpen onClose={handleClose}>
          <p>Content</p>
        </Modal>
      );

      fireEvent.keyDown(document, { key: "Escape" });
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it("does not close on Escape when closeOnEscape is false", () => {
      const handleClose = vi.fn();
      render(
        <Modal isOpen onClose={handleClose} closeOnEscape={false}>
          <p>Content</p>
        </Modal>
      );

      fireEvent.keyDown(document, { key: "Escape" });
      expect(handleClose).not.toHaveBeenCalled();
    });
  });

  describe("focus management", () => {
    it("modal container is focusable", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      const modal = screen.getByRole("dialog").querySelector(".modal");
      expect(modal).toHaveAttribute("tabIndex", "-1");
    });
  });

  describe("accessibility", () => {
    it("has role dialog", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has aria-modal attribute", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby when title is provided", () => {
      render(
        <Modal isOpen onClose={() => {}} title="Modal Title">
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-labelledby", "modal-title");
    });

    it("has aria-describedby when description is provided", () => {
      render(
        <Modal isOpen onClose={() => {}} description="Modal description">
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-describedby", "modal-description");
    });

    it("close button has aria-label", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(screen.getByLabelText("Close modal")).toBeInTheDocument();
    });
  });

  describe("body scroll lock", () => {
    afterEach(() => {
      document.body.style.overflow = "";
    });

    it("locks body scroll when open", () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(document.body.style.overflow).toBe("hidden");
    });

    it("unlocks body scroll when closed", () => {
      const { rerender } = render(
        <Modal isOpen onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(document.body.style.overflow).toBe("hidden");

      rerender(
        <Modal isOpen={false} onClose={() => {}}>
          <p>Content</p>
        </Modal>
      );

      expect(document.body.style.overflow).toBe("");
    });
  });
});

describe("ConfirmModal", () => {
  describe("rendering", () => {
    it("renders title and message", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Confirm Delete"
          message="Are you sure you want to delete this item?"
        />
      );

      expect(screen.getByText("Confirm Delete")).toBeInTheDocument();
      expect(screen.getByText("Are you sure you want to delete this item?")).toBeInTheDocument();
    });

    it("renders default button texts", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Confirm"
          message="Confirm action?"
        />
      );

      expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    });

    it("renders custom button texts", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Delete"
          message="Delete this?"
          confirmText="Yes, delete"
          cancelText="No, keep it"
        />
      );

      expect(screen.getByRole("button", { name: "Yes, delete" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "No, keep it" })).toBeInTheDocument();
    });
  });

  describe("actions", () => {
    it("calls onConfirm when confirm button is clicked", () => {
      const handleConfirm = vi.fn();
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={handleConfirm}
          title="Confirm"
          message="Confirm?"
        />
      );

      fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
      expect(handleConfirm).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when cancel button is clicked", () => {
      const handleClose = vi.fn();
      render(
        <ConfirmModal
          isOpen
          onClose={handleClose}
          onConfirm={() => {}}
          title="Confirm"
          message="Confirm?"
        />
      );

      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("variants", () => {
    it("applies danger variant styles", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Delete"
          message="Delete this?"
          variant="danger"
        />
      );

      const confirmButton = screen.getByRole("button", { name: "Confirm" });
      expect(confirmButton).toHaveClass("bg-[var(--accent-peak)]");
    });

    it("applies warning variant styles", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Warning"
          message="Are you sure?"
          variant="warning"
        />
      );

      const confirmButton = screen.getByRole("button", { name: "Confirm" });
      expect(confirmButton).toHaveClass("bg-[var(--accent-warm)]");
    });

    it("applies default variant styles", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Confirm"
          message="Proceed?"
          variant="default"
        />
      );

      const confirmButton = screen.getByRole("button", { name: "Confirm" });
      expect(confirmButton).toHaveClass("bg-[var(--accent-safe)]");
    });
  });

  describe("loading state", () => {
    it("shows loading text when isLoading is true", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Confirm"
          message="Confirm?"
          isLoading
        />
      );

      expect(screen.getByRole("button", { name: "Loading..." })).toBeInTheDocument();
    });

    it("disables buttons when loading", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Confirm"
          message="Confirm?"
          isLoading
        />
      );

      expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    });

    it("applies loading styles to confirm button", () => {
      render(
        <ConfirmModal
          isOpen
          onClose={() => {}}
          onConfirm={() => {}}
          title="Confirm"
          message="Confirm?"
          isLoading
        />
      );

      const confirmButton = screen.getByRole("button", { name: "Loading..." });
      expect(confirmButton).toHaveClass("opacity-50", "cursor-not-allowed");
    });
  });
});
