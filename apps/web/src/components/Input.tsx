import type { InputHTMLAttributes } from "react";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export function Input({ className = "", type = "text", ...props }: InputProps) {
  return (
    <input
      type={type}
      className={`w-full rounded-md border border-black/15 bg-bg px-3 py-1.5 text-sm text-fg placeholder:text-muted focus-visible:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 disabled:opacity-50 dark:border-white/15 ${className}`}
      {...props}
    />
  );
}
