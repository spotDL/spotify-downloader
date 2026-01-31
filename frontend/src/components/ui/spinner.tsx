import { type HTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg";
}

export const Spinner = forwardRef<HTMLDivElement, SpinnerProps>(
  ({ className, size = "md", ...props }, ref) => {
    const sizes = {
      sm: "h-4 w-4 border-2",
      md: "h-8 w-8 border-2",
      lg: "h-12 w-12 border-3",
    };

    return (
      <div
        ref={ref}
        className={twMerge(
          clsx(
            "animate-spin rounded-full border-gray-700 border-t-blue-500",
            sizes[size],
            className
          )
        )}
        {...props}
      />
    );
  }
);

Spinner.displayName = "Spinner";

export interface LoadingProps extends HTMLAttributes<HTMLDivElement> {
  text?: string;
  size?: "sm" | "md" | "lg";
}

export const Loading = forwardRef<HTMLDivElement, LoadingProps>(
  ({ className, text = "Loading...", size = "md", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={twMerge(
          clsx("flex flex-col items-center justify-center gap-3", className)
        )}
        {...props}
      >
        <Spinner size={size} />
        {text && <p className="text-gray-400 text-sm">{text}</p>}
      </div>
    );
  }
);

Loading.displayName = "Loading";
