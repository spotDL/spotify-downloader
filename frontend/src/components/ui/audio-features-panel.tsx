import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { AudioFeatures } from "@/types";
import { KeySignatureBadge } from "./key-signature-badge";
import { TempoVisualizer, TempoLabel } from "./tempo-visualizer";

export interface AudioFeaturesPanelProps {
  /** Audio features data */
  features: AudioFeatures;
  /** Display variant */
  variant?: "full" | "compact";
  /** Additional class names */
  className?: string;
}

// Feature metadata for display
interface FeatureInfo {
  key: keyof AudioFeatures;
  label: string;
  tooltip: string;
  isPercentage: boolean; // Whether the value is 0-1 and should be shown as percentage
}

const FEATURE_INFO: FeatureInfo[] = [
  {
    key: "energy",
    label: "Energy",
    tooltip: "How intense and active the track feels",
    isPercentage: true,
  },
  {
    key: "danceability",
    label: "Danceability",
    tooltip: "How suitable for dancing based on tempo, rhythm, and beat",
    isPercentage: true,
  },
  {
    key: "valence",
    label: "Valence",
    tooltip: "Musical positiveness - high = happy, low = sad",
    isPercentage: true,
  },
  {
    key: "speechiness",
    label: "Speechiness",
    tooltip: "Presence of spoken words",
    isPercentage: true,
  },
  {
    key: "acousticness",
    label: "Acousticness",
    tooltip: "Confidence the track is acoustic",
    isPercentage: true,
  },
  {
    key: "instrumentalness",
    label: "Instrumentalness",
    tooltip: "Whether the track has no vocals",
    isPercentage: true,
  },
  {
    key: "liveness",
    label: "Liveness",
    tooltip: "Probability of a live audience",
    isPercentage: true,
  },
];

// Top features for compact view
const COMPACT_FEATURES: (keyof AudioFeatures)[] = [
  "energy",
  "danceability",
  "valence",
  "acousticness",
];

// Get color based on intensity level
function getIntensityColor(value: number): string {
  const percentage = value * 100;
  if (percentage <= 33) return "var(--accent-cool)";
  if (percentage <= 66) return "var(--accent-warm)";
  return "var(--accent-needle)";
}

// Get color class based on intensity level
function getIntensityColorClass(value: number): string {
  const percentage = value * 100;
  if (percentage <= 33) return "bg-[var(--accent-cool)]";
  if (percentage <= 66) return "bg-[var(--accent-warm)]";
  return "bg-[var(--accent-needle)]";
}

// Format time signature
function formatTimeSignature(timeSig: number | null): string {
  if (timeSig === null) return "--/4";
  return `${timeSig}/4`;
}

// Feature progress bar component
interface FeatureBarProps {
  label: string;
  value: number | null;
  tooltip: string;
}

function FeatureBar({ label, value, tooltip }: FeatureBarProps) {
  const displayValue = value ?? 0;
  const percentage = displayValue * 100;
  const color = getIntensityColor(displayValue);

  return (
    <div className="group" title={tooltip}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors">
          {label}
        </span>
        <span
          className="text-xs font-mono font-medium"
          style={{ color }}
        >
          {value !== null ? `${Math.round(percentage)}%` : "--"}
        </span>
      </div>
      <div className="h-1.5 bg-[var(--bg-surface)] rounded-full overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-500 ease-out",
            getIntensityColorClass(displayValue)
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Comprehensive panel showing audio features with visual bars
 */
export function AudioFeaturesPanel({
  features,
  variant = "full",
  className,
}: AudioFeaturesPanelProps) {
  const featuresToShow = variant === "compact"
    ? FEATURE_INFO.filter((f) => COMPACT_FEATURES.includes(f.key))
    : FEATURE_INFO;

  return (
    <div
      className={twMerge(
        clsx(
          "bg-[var(--bg-panel)] border border-[var(--color-border-subtle)]",
          "rounded-2xl p-5",
          "transition-all duration-200",
          "hover:border-[var(--color-border)]"
        ),
        className
      )}
    >
      {/* Header with Key, Tempo, Time Signature */}
      <div className="flex flex-wrap items-center gap-4 mb-5 pb-4 border-b border-[var(--color-border-subtle)]">
        {/* Tempo */}
        <div className="flex-shrink-0">
          {variant === "full" ? (
            <TempoVisualizer bpm={features.bpm} size="md" animated={true} />
          ) : (
            <TempoLabel bpm={features.bpm} showCategory={false} />
          )}
        </div>

        {/* Key Signature */}
        <KeySignatureBadge
          keyNum={features.key}
          mode={features.mode}
          size={variant === "full" ? "md" : "sm"}
        />

        {/* Time Signature */}
        <div
          className={clsx(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-lg",
            "bg-[var(--bg-surface)] border border-[var(--color-border-subtle)]",
            "text-[var(--color-text-secondary)]"
          )}
          title="Time Signature"
        >
          <svg
            className="w-3.5 h-3.5 opacity-70"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="font-mono text-sm font-medium">
            {formatTimeSignature(features.time_signature)}
          </span>
        </div>

        {/* Loudness (only in full view) */}
        {variant === "full" && features.loudness !== null && (
          <div
            className={clsx(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-lg",
              "bg-[var(--bg-surface)] border border-[var(--color-border-subtle)]",
              "text-[var(--color-text-secondary)]"
            )}
            title="Average Loudness (dB)"
          >
            <svg
              className="w-3.5 h-3.5 opacity-70"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
              />
            </svg>
            <span className="font-mono text-sm font-medium">
              {Math.round(features.loudness)} dB
            </span>
          </div>
        )}
      </div>

      {/* Feature bars */}
      <div className={clsx(
        "grid gap-4",
        variant === "full" ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1"
      )}>
        {featuresToShow.map((featureInfo) => (
          <FeatureBar
            key={featureInfo.key}
            label={featureInfo.label}
            value={features[featureInfo.key] as number | null}
            tooltip={featureInfo.tooltip}
          />
        ))}
      </div>

      {/* Compact view "See more" hint */}
      {variant === "compact" && (
        <p className="mt-4 text-xs text-[var(--color-text-dim)] text-center">
          {FEATURE_INFO.length - COMPACT_FEATURES.length} more features available
        </p>
      )}
    </div>
  );
}

/**
 * Compact inline feature summary
 */
export interface AudioFeaturesSummaryProps {
  features: AudioFeatures;
  className?: string;
}

export function AudioFeaturesSummary({
  features,
  className,
}: AudioFeaturesSummaryProps) {
  const highlights = [
    { label: "Energy", value: features.energy },
    { label: "Danceability", value: features.danceability },
    { label: "Valence", value: features.valence },
  ].filter((h) => h.value !== null);

  return (
    <div className={twMerge("flex flex-wrap items-center gap-3", className)}>
      {/* BPM */}
      {features.bpm !== null && (
        <span className="text-sm font-mono text-[var(--color-text-secondary)]">
          <span className="font-semibold">{Math.round(features.bpm)}</span> BPM
        </span>
      )}

      {/* Key */}
      {features.key !== null && (
        <KeySignatureBadge
          keyNum={features.key}
          mode={features.mode}
          size="sm"
        />
      )}

      {/* Feature highlights */}
      {highlights.map((h) => (
        <span
          key={h.label}
          className="text-sm text-[var(--color-text-muted)]"
        >
          <span className="font-medium">{h.label}:</span>{" "}
          <span
            className="font-mono"
            style={{ color: getIntensityColor(h.value!) }}
          >
            {Math.round(h.value! * 100)}%
          </span>
        </span>
      ))}
    </div>
  );
}

/**
 * Single audio feature display for use in grids/lists
 */
export interface SingleFeatureProps {
  label: string;
  value: number | null;
  tooltip?: string;
  showBar?: boolean;
  className?: string;
}

export function SingleFeature({
  label,
  value,
  tooltip,
  showBar = true,
  className,
}: SingleFeatureProps) {
  const displayValue = value ?? 0;
  const percentage = displayValue * 100;
  const color = getIntensityColor(displayValue);

  return (
    <div className={twMerge("flex flex-col", className)} title={tooltip}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
        <span className="text-xs font-mono font-medium" style={{ color }}>
          {value !== null ? `${Math.round(percentage)}%` : "--"}
        </span>
      </div>
      {showBar && (
        <div className="h-1 bg-[var(--bg-surface)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${percentage}%`,
              backgroundColor: color,
            }}
          />
        </div>
      )}
    </div>
  );
}

export default AudioFeaturesPanel;
