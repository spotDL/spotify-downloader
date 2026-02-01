import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface KeySignatureBadgeProps {
  /** Key number 0-11 (C, C#, D, D#, E, F, F#, G, G#, A, A#, B) */
  keyNum: number | null;
  /** Mode: 0 = minor, 1 = major */
  mode: number | null;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional class names */
  className?: string;
}

// Key number to note name mapping
const KEY_NAMES: Record<number, string> = {
  0: "C",
  1: "C#",
  2: "D",
  3: "D#",
  4: "E",
  5: "F",
  6: "F#",
  7: "G",
  8: "G#",
  9: "A",
  10: "A#",
  11: "B",
};

// Alternative names for sharp keys (using flats)
const KEY_NAMES_FLAT: Record<number, string> = {
  1: "Db",
  3: "Eb",
  6: "Gb",
  8: "Ab",
  10: "Bb",
};

// Key families for color coding
// Natural keys: C, F, G -> accent-safe (green)
// Sharp/Flat common: D, A, E -> accent-needle (orange)
// More chromatic: B, F#, C# -> accent-cool (blue)
type KeyFamily = "natural" | "common" | "chromatic";

const KEY_FAMILIES: Record<number, KeyFamily> = {
  0: "natural",  // C
  1: "chromatic", // C#
  2: "common",   // D
  3: "chromatic", // D#
  4: "common",   // E
  5: "natural",  // F
  6: "chromatic", // F#
  7: "natural",  // G
  8: "chromatic", // G#
  9: "common",   // A
  10: "chromatic", // A#
  11: "chromatic", // B
};

const familyColors: Record<KeyFamily, { bg: string; text: string; border: string }> = {
  natural: {
    bg: "bg-[var(--accent-safe)]/10",
    text: "text-[var(--accent-safe)]",
    border: "border-[var(--accent-safe)]/30",
  },
  common: {
    bg: "bg-[var(--accent-needle)]/10",
    text: "text-[var(--accent-needle)]",
    border: "border-[var(--accent-needle)]/30",
  },
  chromatic: {
    bg: "bg-[var(--accent-cool)]/10",
    text: "text-[var(--accent-cool)]",
    border: "border-[var(--accent-cool)]/30",
  },
};

// Minor keys get slightly muted colors
const familyColorsMinor: Record<KeyFamily, { bg: string; text: string; border: string }> = {
  natural: {
    bg: "bg-[var(--accent-safe)]/5",
    text: "text-[var(--accent-safe)]/80",
    border: "border-[var(--accent-safe)]/20",
  },
  common: {
    bg: "bg-[var(--accent-needle)]/5",
    text: "text-[var(--accent-needle)]/80",
    border: "border-[var(--accent-needle)]/20",
  },
  chromatic: {
    bg: "bg-[var(--accent-cool)]/5",
    text: "text-[var(--accent-cool)]/80",
    border: "border-[var(--accent-cool)]/20",
  },
};

const sizeClasses = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3 py-1.5 text-base",
};

/**
 * Badge displaying musical key signature (e.g., "C Major", "A Minor")
 * Color-coded by key family with muted colors for minor keys
 */
export function KeySignatureBadge({
  keyNum,
  mode,
  size = "md",
  className,
}: KeySignatureBadgeProps) {
  // Handle null values
  if (keyNum === null || keyNum < 0 || keyNum > 11) {
    return (
      <span
        className={twMerge(
          clsx(
            "inline-flex items-center gap-1.5 rounded-lg font-medium border",
            "bg-[var(--bg-surface)] text-[var(--color-text-muted)] border-[var(--color-border-subtle)]",
            sizeClasses[size]
          ),
          className
        )}
      >
        Unknown
      </span>
    );
  }

  const keyName = KEY_NAMES[keyNum];
  const isMajor = mode === 1;
  const modeName = isMajor ? "Major" : "Minor";
  const family = KEY_FAMILIES[keyNum];
  const colors = isMajor ? familyColors[family] : familyColorsMinor[family];

  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center gap-1.5 rounded-lg font-medium border",
          "transition-colors duration-200",
          colors.bg,
          colors.text,
          colors.border,
          sizeClasses[size]
        ),
        className
      )}
      title={`Key: ${keyName} ${modeName}`}
    >
      {/* Musical note icon */}
      <svg
        className={clsx(
          "flex-shrink-0",
          size === "sm" && "w-3 h-3",
          size === "md" && "w-3.5 h-3.5",
          size === "lg" && "w-4 h-4"
        )}
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path d="M18 3v12.535a3.5 3.5 0 1 1-2-3.164V6.121l-8 1.778v8.566a3.5 3.5 0 1 1-2-3.164V5.107a1 1 0 0 1 .757-.97l10-2.222A1 1 0 0 1 18 3z" />
      </svg>
      <span className="font-semibold">{keyName}</span>
      <span className="opacity-70">{modeName}</span>
    </span>
  );
}

/**
 * Get human-readable key signature string
 */
export function getKeySignatureString(keyNum: number | null, mode: number | null): string {
  if (keyNum === null || keyNum < 0 || keyNum > 11) {
    return "Unknown";
  }
  const keyName = KEY_NAMES[keyNum];
  const modeName = mode === 1 ? "Major" : "Minor";
  return `${keyName} ${modeName}`;
}

/**
 * Get alternate key name (flat instead of sharp)
 */
export function getAlternateKeyName(keyNum: number): string | null {
  return KEY_NAMES_FLAT[keyNum] || null;
}

export default KeySignatureBadge;
