import { forwardRef, type InputHTMLAttributes } from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "../../lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, label, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-foreground">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          className={cn(
            "flex h-9 w-full rounded-md border bg-surface px-3 py-1 text-sm text-foreground",
            "placeholder:text-faint",
            "transition-colors outline-none",
            "focus-visible:ring-2 focus-visible:ring-ring/40",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error
              ? "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/40"
              : "border-border focus-visible:border-ring",
            className,
          )}
          {...props}
        />
        {error && (
          <p className="mt-1.5 flex items-center gap-1.5 text-sm text-destructive">
            <AlertCircle className="size-4 shrink-0" />
            {error}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
