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
            "animate-spin rounded-full",
            "border-zinc-800 border-t-emerald-500",
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

// Audio waveform loading animation
export const WaveformLoader = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement> & { bars?: number }
>(({ className, bars = 5, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={twMerge(
        clsx("flex items-center justify-center gap-1 h-6", className)
      )}
      {...props}
    >
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className="waveform-bar h-4"
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
});

WaveformLoader.displayName = "WaveformLoader";

// Equalizer loading animation
export const EqualizerLoader = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={twMerge(clsx("equalizer", className))}
      {...props}
    >
      <div className="equalizer-bar" />
      <div className="equalizer-bar" />
      <div className="equalizer-bar" />
      <div className="equalizer-bar" />
      <div className="equalizer-bar" />
    </div>
  );
});

EqualizerLoader.displayName = "EqualizerLoader";

export interface LoadingProps extends HTMLAttributes<HTMLDivElement> {
  text?: string;
  size?: "sm" | "md" | "lg";
  variant?: "spinner" | "waveform" | "equalizer";
}

export const Loading = forwardRef<HTMLDivElement, LoadingProps>(
  ({ className, text = "Loading...", size = "md", variant = "waveform", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={twMerge(
          clsx("flex flex-col items-center justify-center gap-4", className)
        )}
        {...props}
      >
        {variant === "spinner" && <Spinner size={size} />}
        {variant === "waveform" && <WaveformLoader />}
        {variant === "equalizer" && <EqualizerLoader />}
        {text && (
          <p className="text-zinc-400 text-sm font-medium animate-pulse">
            {text}
          </p>
        )}
      </div>
    );
  }
);

Loading.displayName = "Loading";

// Skeleton loader for content placeholders
export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant = "text", width, height, style, ...props }, ref) => {
    const variants = {
      text: "h-4 rounded",
      circular: "rounded-full",
      rectangular: "rounded-xl",
    };

    return (
      <div
        ref={ref}
        className={twMerge(
          clsx("shimmer", variants[variant], className)
        )}
        style={{
          width: width ?? (variant === "text" ? "100%" : undefined),
          height: height ?? (variant === "circular" ? width : undefined),
          ...style,
        }}
        {...props}
      />
    );
  }
);

Skeleton.displayName = "Skeleton";
