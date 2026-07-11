import type { InputHTMLAttributes } from "react";
import { cn } from "../lib/utils";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

// A bare token-styled input (the ui/input primitive adds a label/error wrapper;
// this keeps the legacy single-element API that call sites rely on).
export function Input({ className, type = "text", ...props }: InputProps) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-border bg-surface px-3 py-1 text-sm text-foreground",
        "placeholder:text-faint transition-colors outline-none",
        "focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
