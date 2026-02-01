import { useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface ModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when modal should close */
  onClose: () => void;
  /** Modal title */
  title?: string;
  /** Modal description */
  description?: string;
  /** Size variant */
  size?: "sm" | "md" | "lg" | "xl" | "full";
  /** Whether clicking backdrop closes modal */
  closeOnBackdropClick?: boolean;
  /** Whether pressing Escape closes modal */
  closeOnEscape?: boolean;
  /** Show close button */
  showCloseButton?: boolean;
  /** Modal content */
  children: React.ReactNode;
  /** Footer content (buttons, etc.) */
  footer?: React.ReactNode;
  /** Additional class names for modal container */
  className?: string;
}

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  full: "max-w-4xl",
};

// Close icon
const CloseIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  size = "md",
  closeOnBackdropClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  children,
  footer,
  className,
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Handle escape key
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && closeOnEscape) {
        onClose();
      }
    },
    [closeOnEscape, onClose]
  );

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && closeOnBackdropClick) {
      onClose();
    }
  };

  // Focus management
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      modalRef.current?.focus();

      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";

      return () => {
        document.removeEventListener("keydown", handleEscape);
        document.body.style.overflow = "";
        previousActiveElement.current?.focus();
      };
    }
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  const modalContent = (
    <div
      className="modal-backdrop fixed inset-0 z-[100] flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      aria-modal="true"
      role="dialog"
      aria-labelledby={title ? "modal-title" : undefined}
      aria-describedby={description ? "modal-description" : undefined}
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className={twMerge(
          clsx(
            "modal relative w-full",
            "bg-[var(--bg-panel)] border border-[var(--color-border)]",
            "rounded-2xl shadow-2xl",
            "animate-scale-in",
            "outline-none",
            sizeClasses[size]
          ),
          className
        )}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="modal-header flex items-start justify-between p-6 pb-0">
            <div className="flex-1 pr-4">
              {title && (
                <h2
                  id="modal-title"
                  className="text-xl font-semibold text-[var(--color-text-primary)]"
                >
                  {title}
                </h2>
              )}
              {description && (
                <p
                  id="modal-description"
                  className="mt-1 text-sm text-[var(--color-text-muted)]"
                >
                  {description}
                </p>
              )}
            </div>
            {showCloseButton && (
              <button
                onClick={onClose}
                className={clsx(
                  "p-1.5 rounded-lg",
                  "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
                  "hover:bg-[var(--bg-hover)]",
                  "transition-colors duration-150",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)]"
                )}
                aria-label="Close modal"
              >
                <CloseIcon />
              </button>
            )}
          </div>
        )}

        {/* Body */}
        <div className="modal-body p-6">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="modal-footer flex items-center justify-end gap-3 p-6 pt-0 border-t border-[var(--color-border-subtle)]">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}

/**
 * Confirmation modal variant
 */
export interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "default";
  isLoading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  isLoading = false,
}: ConfirmModalProps) {
  const confirmButtonClasses = clsx(
    "px-4 py-2 rounded-xl font-medium text-sm",
    "transition-all duration-200",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-panel)]",
    {
      "bg-[var(--accent-peak)] hover:bg-red-500 text-white focus-visible:ring-[var(--accent-peak)]":
        variant === "danger",
      "bg-[var(--accent-warm)] hover:bg-amber-400 text-black focus-visible:ring-[var(--accent-warm)]":
        variant === "warning",
      "bg-[var(--accent-safe)] hover:bg-emerald-400 text-white focus-visible:ring-[var(--accent-safe)]":
        variant === "default",
    },
    isLoading && "opacity-50 cursor-not-allowed"
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <button
            onClick={onClose}
            disabled={isLoading}
            className={clsx(
              "px-4 py-2 rounded-xl font-medium text-sm",
              "bg-[var(--bg-surface)] text-[var(--color-text-secondary)]",
              "hover:bg-[var(--bg-hover)] hover:text-[var(--color-text-primary)]",
              "transition-colors duration-150",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border)]"
            )}
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={confirmButtonClasses}
          >
            {isLoading ? "Loading..." : confirmText}
          </button>
        </>
      }
    >
      <p className="text-[var(--color-text-secondary)]">{message}</p>
    </Modal>
  );
}

export default Modal;
