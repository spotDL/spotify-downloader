import { type HTMLAttributes, useMemo } from "react";
import { cn } from "../../lib/utils";

export interface MeterProps extends HTMLAttributes<HTMLDivElement> {
  /** 0–1 (or 0–max) amount of the meter that is lit. */
  value: number;
  /** Upper bound for `value`. Defaults to 1. */
  max?: number;
  /** Number of discrete cells. */
  cells?: number;
  /** CSS color for lit cells. Defaults to the primary amber. */
  color?: string;
  /** Pulse the last lit cell (active/in-flight state). */
  active?: boolean;
  /** Cell height. */
  size?: "sm" | "md" | "lg";
  label?: string;
}

const sizeClasses = { sm: "h-1.5", md: "h-2", lg: "h-3" };

/**
 * Segmented LED meter — the Control Room signature. Progress, match quality,
 * and audio features all render in this one language (the TUI mirrors it
 * with ▰▱ glyphs).
 */
export function Meter({
  value,
  max = 1,
  cells = 12,
  color,
  active = false,
  size = "md",
  label,
  className,
  style,
  ...props
}: MeterProps) {
  const lit = useMemo(() => {
    const ratio = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;
    return Math.round(ratio * cells);
  }, [value, max, cells]);

  return (
    <div
      role="meter"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label={label}
      className={cn("meter", sizeClasses[size], className)}
      style={{
        ...style,
        ["--meter-cells" as string]: cells,
        ...(color ? { ["--meter-color" as string]: color } : {}),
      }}
      {...props}
    >
      {Array.from({ length: cells }, (_, i) => (
        <span
          key={i}
          className="meter-cell"
          data-lit={i < lit || undefined}
          data-active={(active && i === lit - 1) || undefined}
        />
      ))}
    </div>
  );
}

/** Maps a 0–100 score onto meter color stops (destructive → warning → success). */
export function scoreColor(score: number): string {
  if (score >= 75) return "var(--success)";
  if (score >= 45) return "var(--warning)";
  return "var(--destructive)";
}
