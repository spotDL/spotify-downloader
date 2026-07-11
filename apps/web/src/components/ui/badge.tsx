import { type HTMLAttributes, forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const badgeVariants = cva(
  cn("inline-flex items-center gap-1.5 rounded-full border font-medium", "transition-colors"),
  {
    variants: {
      variant: {
        default: "border-border bg-surface text-muted-foreground",
        success: "border-success/30 bg-success/10 text-success",
        warning: "border-warning/30 bg-warning/10 text-warning",
        error: "border-destructive/30 bg-destructive/10 text-destructive",
        info: "border-info/30 bg-info/10 text-info",
        premium: "border-primary/30 bg-primary/10 text-primary",
        muted: "border-border/60 bg-transparent text-faint",
      },
      size: {
        sm: "px-2 py-0.5 text-[10px]",
        md: "px-2.5 py-0.5 text-xs",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  pulse?: boolean;
}

const pulseColors: Record<string, string> = {
  default: "bg-muted-foreground",
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-destructive",
  info: "bg-info",
  premium: "bg-primary",
  muted: "bg-faint",
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", size = "md", pulse = false, children, ...props }, ref) => {
    const dot = pulseColors[variant ?? "default"] ?? pulseColors.default;
    return (
      <span ref={ref} className={cn(badgeVariants({ variant, size }), className)} {...props}>
        {pulse && (
          <span className="relative flex size-1.5">
            <span
              className={cn(
                "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
                dot,
              )}
            />
            <span className={cn("relative inline-flex size-1.5 rounded-full", dot)} />
          </span>
        )}
        {children}
      </span>
    );
  },
);

Badge.displayName = "Badge";

// Platform-specific badge — brand identity dot + label. Only platforms whose
// brand color token exists in this app's theme are supported.
export interface PlatformBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  platform: "spotify" | "apple_music" | "deezer" | "youtube" | "soundcloud" | "musicbrainz";
}

const platformDotColor: Record<PlatformBadgeProps["platform"], string> = {
  spotify: "bg-spotify",
  apple_music: "bg-apple",
  deezer: "bg-deezer",
  youtube: "bg-youtube",
  soundcloud: "bg-soundcloud",
  musicbrainz: "bg-musicbrainz",
};

const platformNames: Record<PlatformBadgeProps["platform"], string> = {
  spotify: "Spotify",
  apple_music: "Apple Music",
  deezer: "Deezer",
  youtube: "YouTube",
  soundcloud: "SoundCloud",
  musicbrainz: "MusicBrainz",
};

export const PlatformBadge = forwardRef<HTMLSpanElement, PlatformBadgeProps>(
  ({ platform, className, ...props }, ref) => {
    const dot = platformDotColor[platform] ?? platformDotColor.spotify;
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-0.5 text-xs font-medium text-foreground",
          className,
        )}
        {...props}
      >
        <span className={cn("size-1.5 rounded-full", dot)} aria-hidden />
        {platformNames[platform] || platform}
      </span>
    );
  },
);

PlatformBadge.displayName = "PlatformBadge";

export { badgeVariants };
