import { forwardRef, type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = clsx(
      "relative inline-flex items-center justify-center font-medium",
      "rounded-xl transition-all duration-200",
      "focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0b]",
      "disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none",
      "btn-press"
    );

    const variants = {
      primary: clsx(
        "text-white font-semibold",
        "bg-gradient-to-r from-emerald-500 via-emerald-500 to-teal-500",
        "hover:from-emerald-400 hover:via-emerald-400 hover:to-teal-400",
        "shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40",
        "border border-emerald-400/20"
      ),
      secondary: clsx(
        "bg-[#18181b] text-zinc-100",
        "hover:bg-[#27272a]",
        "border border-zinc-800 hover:border-zinc-700"
      ),
      outline: clsx(
        "bg-transparent text-zinc-300",
        "border border-zinc-700 hover:border-zinc-500",
        "hover:bg-zinc-800/50"
      ),
      ghost: clsx(
        "bg-transparent text-zinc-400",
        "hover:text-zinc-100 hover:bg-zinc-800/50"
      ),
      danger: clsx(
        "bg-gradient-to-r from-red-600 to-red-500 text-white font-semibold",
        "hover:from-red-500 hover:to-red-400",
        "shadow-lg shadow-red-500/25 hover:shadow-red-500/40",
        "border border-red-400/20"
      ),
    };

    const sizes = {
      sm: "px-3 py-1.5 text-sm gap-1.5",
      md: "px-5 py-2.5 text-sm gap-2",
      lg: "px-7 py-3.5 text-base gap-2.5",
    };

    return (
      <button
        ref={ref}
        className={twMerge(
          clsx(baseStyles, variants[variant], sizes[size], className)
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
