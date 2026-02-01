import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ScoreLevel } from "@/types";

export interface MatchScoreGaugeProps {
  /** Score value from 0 to 100 */
  score: number;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Show the score label */
  showLabel?: boolean;
  /** Animate the gauge fill on mount */
  animated?: boolean;
  /** Additional class names */
  className?: string;
}

const sizeConfig = {
  sm: { size: 48, strokeWidth: 4, fontSize: "text-xs" },
  md: { size: 64, strokeWidth: 5, fontSize: "text-sm" },
  lg: { size: 96, strokeWidth: 6, fontSize: "text-lg" },
};

function getScoreLevel(score: number): ScoreLevel {
  if (score >= 90) return "high";
  if (score >= 70) return "medium";
  return "low";
}

function getScoreColor(level: ScoreLevel): string {
  switch (level) {
    case "high":
      return "var(--accent-safe)";
    case "medium":
      return "var(--accent-warm)";
    case "low":
      return "var(--accent-peak)";
  }
}

/**
 * Circular gauge visualization for match scores
 * Uses VU meter-inspired color coding: green (90+), yellow (70-89), red (<70)
 */
export function MatchScoreGauge({
  score,
  size = "md",
  showLabel = true,
  animated = true,
  className,
}: MatchScoreGaugeProps) {
  const config = sizeConfig[size];
  const radius = (config.size - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const normalizedScore = Math.min(100, Math.max(0, score));
  const strokeDashoffset = circumference * (1 - normalizedScore / 100);
  const level = getScoreLevel(normalizedScore);
  const color = getScoreColor(level);

  return (
    <div
      className={twMerge(
        clsx("score-gauge relative inline-flex items-center justify-center"),
        className
      )}
      data-score={level}
      style={{ "--score": normalizedScore, "--score-color": color } as React.CSSProperties}
    >
      <svg
        width={config.size}
        height={config.size}
        viewBox={`0 0 ${config.size} ${config.size}`}
        className="transform -rotate-90"
      >
        {/* Background track */}
        <circle
          cx={config.size / 2}
          cy={config.size / 2}
          r={radius}
          fill="none"
          stroke="var(--bg-surface)"
          strokeWidth={config.strokeWidth}
        />
        {/* Score arc */}
        <circle
          cx={config.size / 2}
          cy={config.size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={config.strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={clsx(
            animated && "animate-[scoreGaugeFill_1s_ease-out_forwards]"
          )}
          style={{
            "--initial-offset": circumference,
            transition: animated ? undefined : "stroke-dashoffset 0.3s ease-out",
          } as React.CSSProperties}
        />
      </svg>

      {/* Center label */}
      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={clsx(
              "font-mono font-semibold",
              config.fontSize
            )}
            style={{ color }}
          >
            {Math.round(normalizedScore)}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Horizontal bar version of the match score gauge
 */
export interface MatchScoreBarProps {
  score: number;
  showLabel?: boolean;
  showPercentage?: boolean;
  className?: string;
}

export function MatchScoreBar({
  score,
  showLabel = false,
  showPercentage = true,
  className,
}: MatchScoreBarProps) {
  const normalizedScore = Math.min(100, Math.max(0, score));
  const level = getScoreLevel(normalizedScore);
  const color = getScoreColor(level);

  return (
    <div className={twMerge("w-full", className)}>
      {(showLabel || showPercentage) && (
        <div className="flex items-center justify-between mb-1">
          {showLabel && (
            <span className="text-xs text-[var(--color-text-muted)]">
              Match Score
            </span>
          )}
          {showPercentage && (
            <span
              className="text-xs font-mono font-medium"
              style={{ color }}
            >
              {Math.round(normalizedScore)}%
            </span>
          )}
        </div>
      )}
      <div className="h-2 bg-[var(--bg-surface)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${normalizedScore}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

/**
 * Compact score badge for use in lists
 */
export interface ScoreBadgeProps {
  score: number;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  const normalizedScore = Math.min(100, Math.max(0, score));
  const level = getScoreLevel(normalizedScore);
  const color = getScoreColor(level);

  const bgColorClass = clsx({
    "bg-[var(--accent-safe)]/10": level === "high",
    "bg-[var(--accent-warm)]/10": level === "medium",
    "bg-[var(--accent-peak)]/10": level === "low",
  });

  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center justify-center",
          "px-2 py-0.5 rounded-full",
          "text-xs font-mono font-semibold",
          bgColorClass
        ),
        className
      )}
      style={{ color }}
    >
      {Math.round(normalizedScore)}%
    </span>
  );
}

export default MatchScoreGauge;
