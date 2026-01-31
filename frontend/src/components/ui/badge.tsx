import { type HTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "error" | "info" | "premium";
  size?: "sm" | "md";
  pulse?: boolean;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", size = "md", pulse = false, children, ...props }, ref) => {
    const variants = {
      default: "bg-zinc-800 text-zinc-300 border-zinc-700",
      success: "bg-emerald-950/50 text-emerald-400 border-emerald-800/50",
      warning: "bg-amber-950/50 text-amber-400 border-amber-800/50",
      error: "bg-red-950/50 text-red-400 border-red-800/50",
      info: "bg-sky-950/50 text-sky-400 border-sky-800/50",
      premium: "bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white border-violet-500/30",
    };

    const sizes = {
      sm: "px-2 py-0.5 text-[10px]",
      md: "px-2.5 py-1 text-xs",
    };

    return (
      <span
        ref={ref}
        className={twMerge(
          clsx(
            "inline-flex items-center gap-1.5 rounded-lg font-medium border",
            "transition-colors duration-200",
            variants[variant],
            sizes[size],
            className
          )
        )}
        {...props}
      >
        {pulse && (
          <span className="relative flex h-2 w-2">
            <span className={clsx(
              "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
              variant === "success" && "bg-emerald-400",
              variant === "warning" && "bg-amber-400",
              variant === "error" && "bg-red-400",
              variant === "info" && "bg-sky-400",
              variant === "default" && "bg-zinc-400",
              variant === "premium" && "bg-violet-400"
            )} />
            <span className={clsx(
              "relative inline-flex rounded-full h-2 w-2",
              variant === "success" && "bg-emerald-500",
              variant === "warning" && "bg-amber-500",
              variant === "error" && "bg-red-500",
              variant === "info" && "bg-sky-500",
              variant === "default" && "bg-zinc-500",
              variant === "premium" && "bg-violet-500"
            )} />
          </span>
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";

// Platform-specific badge
export interface PlatformBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  platform: "spotify" | "apple_music" | "deezer" | "youtube" | "youtube_music" | "soundcloud" | "bandcamp";
}

const platformStyles: Record<string, { bg: string; text: string; icon?: string }> = {
  spotify: { bg: "bg-[#1db954]", text: "text-white" },
  apple_music: { bg: "bg-gradient-to-r from-[#fc3c44] to-[#fa233b]", text: "text-white" },
  deezer: { bg: "bg-[#a238ff]", text: "text-white" },
  youtube: { bg: "bg-[#ff0000]", text: "text-white" },
  youtube_music: { bg: "bg-[#ff0000]", text: "text-white" },
  soundcloud: { bg: "bg-gradient-to-r from-[#ff5500] to-[#ff7700]", text: "text-white" },
  bandcamp: { bg: "bg-[#1da0c3]", text: "text-white" },
};

const platformNames: Record<string, string> = {
  spotify: "Spotify",
  apple_music: "Apple Music",
  deezer: "Deezer",
  youtube: "YouTube",
  youtube_music: "YouTube Music",
  soundcloud: "SoundCloud",
  bandcamp: "Bandcamp",
};

export const PlatformBadge = forwardRef<HTMLSpanElement, PlatformBadgeProps>(
  ({ platform, className, ...props }, ref) => {
    const style = platformStyles[platform] || platformStyles.spotify;

    return (
      <span
        ref={ref}
        className={twMerge(
          clsx(
            "inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold",
            "shadow-sm",
            style.bg,
            style.text,
            className
          )
        )}
        {...props}
      >
        {platformNames[platform] || platform}
      </span>
    );
  }
);

PlatformBadge.displayName = "PlatformBadge";
