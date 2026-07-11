import { cn } from "../lib/utils";

export function Spinner({
  label = "Loading",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={label}
      className={cn(
        "inline-block size-5 animate-spin rounded-full border-2 border-current border-t-transparent text-primary",
        className,
      )}
    />
  );
}
