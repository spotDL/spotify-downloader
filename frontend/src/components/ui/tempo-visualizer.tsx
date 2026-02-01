import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { useEffect, useState, useRef } from "react";

export interface TempoVisualizerProps {
  /** Beats per minute */
  bpm: number | null;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Whether to animate the beat indicator */
  animated?: boolean;
  /** Additional class names */
  className?: string;
}

// Tempo categories based on Italian tempo markings
type TempoCategory = {
  name: string;
  minBpm: number;
  maxBpm: number;
};

const TEMPO_CATEGORIES: TempoCategory[] = [
  { name: "Grave", minBpm: 0, maxBpm: 60 },
  { name: "Largo", minBpm: 60, maxBpm: 66 },
  { name: "Adagio", minBpm: 66, maxBpm: 76 },
  { name: "Andante", minBpm: 76, maxBpm: 108 },
  { name: "Moderato", minBpm: 108, maxBpm: 120 },
  { name: "Allegro", minBpm: 120, maxBpm: 156 },
  { name: "Vivace", minBpm: 156, maxBpm: 176 },
  { name: "Presto", minBpm: 176, maxBpm: 999 },
];

function getTempoCategory(bpm: number): string {
  for (const category of TEMPO_CATEGORIES) {
    if (bpm >= category.minBpm && bpm < category.maxBpm) {
      return category.name;
    }
  }
  return "Presto";
}

// Color based on tempo (slower = cooler, faster = warmer)
function getTempoColor(bpm: number): string {
  if (bpm < 76) return "var(--accent-cool)";
  if (bpm < 120) return "var(--accent-safe)";
  if (bpm < 156) return "var(--accent-warm)";
  return "var(--accent-needle)";
}

const sizeConfig = {
  sm: {
    container: "gap-1.5",
    bpmText: "text-lg",
    bpmLabel: "text-[10px]",
    categoryText: "text-xs",
    pulseSize: "w-2 h-2",
    ringSize: "w-4 h-4",
  },
  md: {
    container: "gap-2",
    bpmText: "text-2xl",
    bpmLabel: "text-xs",
    categoryText: "text-sm",
    pulseSize: "w-2.5 h-2.5",
    ringSize: "w-5 h-5",
  },
  lg: {
    container: "gap-3",
    bpmText: "text-4xl",
    bpmLabel: "text-sm",
    categoryText: "text-base",
    pulseSize: "w-3 h-3",
    ringSize: "w-6 h-6",
  },
};

/**
 * Tempo visualizer with BPM display and animated beat indicator
 */
export function TempoVisualizer({
  bpm,
  size = "md",
  animated = true,
  className,
}: TempoVisualizerProps) {
  const config = sizeConfig[size];
  const [isPulsing, setIsPulsing] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Calculate interval for beat animation based on BPM
  useEffect(() => {
    if (!animated || bpm === null || bpm <= 0) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Convert BPM to milliseconds per beat
    const beatInterval = (60 / bpm) * 1000;

    // Trigger pulse on each beat
    intervalRef.current = setInterval(() => {
      setIsPulsing(true);
      setTimeout(() => setIsPulsing(false), Math.min(beatInterval * 0.3, 150));
    }, beatInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [bpm, animated]);

  // Handle null BPM
  if (bpm === null) {
    return (
      <div
        className={twMerge(
          clsx("inline-flex items-center", config.container),
          className
        )}
      >
        <div className="flex flex-col items-center">
          <span
            className={clsx(
              "font-mono font-bold text-[var(--color-text-muted)]",
              config.bpmText
            )}
          >
            --
          </span>
          <span
            className={clsx(
              "uppercase tracking-wider text-[var(--color-text-dim)]",
              config.bpmLabel
            )}
          >
            BPM
          </span>
        </div>
      </div>
    );
  }

  const category = getTempoCategory(bpm);
  const color = getTempoColor(bpm);
  const roundedBpm = Math.round(bpm);

  return (
    <div
      className={twMerge(
        clsx("inline-flex items-center", config.container),
        className
      )}
    >
      {/* Beat indicator */}
      {animated && (
        <div className="relative flex items-center justify-center">
          {/* Outer ring */}
          <div
            className={clsx(
              "absolute rounded-full border-2 transition-all duration-150",
              config.ringSize,
              isPulsing ? "opacity-60 scale-125" : "opacity-30 scale-100"
            )}
            style={{ borderColor: color }}
          />
          {/* Inner pulse dot */}
          <div
            className={clsx(
              "rounded-full transition-all duration-75",
              config.pulseSize,
              isPulsing ? "scale-110" : "scale-100"
            )}
            style={{
              backgroundColor: color,
              boxShadow: isPulsing ? `0 0 12px ${color}` : "none",
            }}
          />
        </div>
      )}

      {/* BPM value */}
      <div className="flex flex-col">
        <div className="flex items-baseline gap-1">
          <span
            className={clsx(
              "font-mono font-bold tracking-tight",
              config.bpmText
            )}
            style={{ color }}
          >
            {roundedBpm}
          </span>
          <span
            className={clsx(
              "uppercase tracking-wider text-[var(--color-text-dim)]",
              config.bpmLabel
            )}
          >
            BPM
          </span>
        </div>
        <span
          className={clsx(
            "font-medium opacity-80",
            config.categoryText
          )}
          style={{ color }}
        >
          {category}
        </span>
      </div>
    </div>
  );
}

/**
 * Compact tempo display without animation
 */
export interface TempoLabelProps {
  bpm: number | null;
  showCategory?: boolean;
  className?: string;
}

export function TempoLabel({
  bpm,
  showCategory = true,
  className,
}: TempoLabelProps) {
  if (bpm === null) {
    return (
      <span
        className={twMerge(
          "font-mono text-sm text-[var(--color-text-muted)]",
          className
        )}
      >
        -- BPM
      </span>
    );
  }

  const category = getTempoCategory(bpm);
  const color = getTempoColor(bpm);
  const roundedBpm = Math.round(bpm);

  return (
    <span
      className={twMerge(
        clsx("inline-flex items-center gap-1.5 font-mono text-sm"),
        className
      )}
      style={{ color }}
    >
      <span className="font-semibold">{roundedBpm} BPM</span>
      {showCategory && (
        <span className="opacity-70">({category})</span>
      )}
    </span>
  );
}

/**
 * Get tempo category name for a given BPM
 */
export function getTempoName(bpm: number | null): string {
  if (bpm === null) return "Unknown";
  return getTempoCategory(bpm);
}

export default TempoVisualizer;
