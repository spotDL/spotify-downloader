import { useState } from "react";
import { clsx } from "clsx";
import { Modal } from "./modal";
import { Button } from "./button";
import type { MetadataReportEntityType, CreateMetadataReportRequest } from "@/types";

export interface ReportModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when modal should close */
  onClose: () => void;
  /** Callback when report is submitted */
  onSubmit: (report: CreateMetadataReportRequest) => Promise<void>;
  /** Entity type being reported */
  entityType: MetadataReportEntityType;
  /** Entity ID */
  entityId: string;
  /** Entity name for display */
  entityName: string;
  /** Available fields to report */
  fields: Array<{
    name: string;
    label: string;
    currentValue: string;
  }>;
}

export function ReportModal({
  isOpen,
  onClose,
  onSubmit,
  entityType,
  entityId,
  entityName,
  fields,
}: ReportModalProps) {
  const [selectedField, setSelectedField] = useState<string>("");
  const [suggestedValue, setSuggestedValue] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedFieldData = fields.find((f) => f.name === selectedField);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedField || !suggestedValue.trim()) {
      setError("Please select a field and provide a suggested value");
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit({
        entity_type: entityType,
        entity_id: entityId,
        field_name: selectedField,
        current_value: selectedFieldData?.currentValue ?? "",
        suggested_value: suggestedValue.trim(),
        description: description.trim() || undefined,
      });

      // Reset form and close
      setSelectedField("");
      setSuggestedValue("");
      setDescription("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit report");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedField("");
    setSuggestedValue("");
    setDescription("");
    setError(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Report Incorrect Data"
      description={`Report an issue with "${entityName}"`}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Field selector */}
        <div>
          <label
            htmlFor="field"
            className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5"
          >
            Which field is incorrect?
          </label>
          <select
            id="field"
            value={selectedField}
            onChange={(e) => {
              setSelectedField(e.target.value);
              setSuggestedValue("");
            }}
            className={clsx(
              "w-full px-3 py-2.5 rounded-xl",
              "bg-[var(--bg-surface)] border border-[var(--color-border)]",
              "text-[var(--color-text-primary)]",
              "focus:outline-none focus:ring-2 focus:ring-[var(--accent-safe)] focus:border-transparent"
            )}
            required
          >
            <option value="">Select a field...</option>
            {fields.map((field) => (
              <option key={field.name} value={field.name}>
                {field.label}
              </option>
            ))}
          </select>
        </div>

        {/* Current value (read-only) */}
        {selectedFieldData && (
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
              Current value
            </label>
            <div
              className={clsx(
                "px-3 py-2.5 rounded-xl",
                "bg-[var(--bg-void)] border border-[var(--color-border-subtle)]",
                "text-[var(--color-text-muted)]"
              )}
            >
              {selectedFieldData.currentValue || <em>Empty</em>}
            </div>
          </div>
        )}

        {/* Suggested value */}
        <div>
          <label
            htmlFor="suggestedValue"
            className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5"
          >
            Correct value
          </label>
          <input
            id="suggestedValue"
            type="text"
            value={suggestedValue}
            onChange={(e) => setSuggestedValue(e.target.value)}
            placeholder="Enter the correct value..."
            className={clsx(
              "w-full px-3 py-2.5 rounded-xl",
              "bg-[var(--bg-surface)] border border-[var(--color-border)]",
              "text-[var(--color-text-primary)]",
              "placeholder:text-[var(--color-text-muted)]",
              "focus:outline-none focus:ring-2 focus:ring-[var(--accent-safe)] focus:border-transparent"
            )}
            required
          />
        </div>

        {/* Description (optional) */}
        <div>
          <label
            htmlFor="description"
            className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5"
          >
            Additional details{" "}
            <span className="text-[var(--color-text-muted)]">(optional)</span>
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Explain why this is incorrect or provide sources..."
            rows={3}
            className={clsx(
              "w-full px-3 py-2.5 rounded-xl resize-none",
              "bg-[var(--bg-surface)] border border-[var(--color-border)]",
              "text-[var(--color-text-primary)]",
              "placeholder:text-[var(--color-text-muted)]",
              "focus:outline-none focus:ring-2 focus:ring-[var(--accent-safe)] focus:border-transparent"
            )}
          />
        </div>

        {/* Error message */}
        {error && (
          <div className="px-3 py-2 rounded-lg bg-[var(--accent-peak)]/10 text-[var(--accent-peak)] text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={!selectedField || !suggestedValue.trim()}
          >
            Submit Report
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/**
 * Button to trigger the report modal
 */
export interface ReportButtonProps {
  onClick: () => void;
  className?: string;
}

export function ReportButton({ onClick, className }: ReportButtonProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg",
        "text-sm text-[var(--color-text-muted)]",
        "hover:text-[var(--accent-peak)] hover:bg-[var(--accent-peak)]/10",
        "transition-colors duration-150",
        className
      )}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      Report Incorrect Data
    </button>
  );
}

export default ReportModal;
