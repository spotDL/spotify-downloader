import { useState, useEffect, useCallback } from "react";
import { clsx } from "clsx";
import { Button } from "./button";
import { useAuthStore } from "@/stores/auth";

interface RefreshMetadataButtonProps {
  /** Unique entity ID for tracking cooldown per entity */
  entityId: string;
  /** Function to refresh metadata from source platform */
  onRefresh: () => Promise<void>;
  /** Optional function to enrich from external sources (MusicBrainz, etc.) */
  onEnrich?: () => Promise<void>;
  className?: string;
  variant?: "default" | "ghost" | "outline" | "icon";
  size?: "sm" | "md" | "lg";
}

/**
 * Get cooldown key for localStorage
 */
function getCooldownKey(entityId: string): string {
  return `spotdl_refresh_cooldown_${entityId}`;
}

/**
 * Get the remaining cooldown end timestamp from localStorage
 */
function getCooldownEnd(entityId: string): number {
  const key = getCooldownKey(entityId);
  const cooldownEnd = localStorage.getItem(key);
  if (!cooldownEnd) return 0;

  const endTime = parseInt(cooldownEnd, 10);
  if (isNaN(endTime)) return 0;

  return endTime;
}

/**
 * Get remaining cooldown time in milliseconds
 */
function getRemainingCooldown(entityId: string): number {
  const endTime = getCooldownEnd(entityId);
  if (!endTime) return 0;

  const remaining = endTime - Date.now();
  return remaining > 0 ? remaining : 0;
}

/**
 * Format remaining time as human-readable string
 */
function formatRemainingTime(ms: number): string {
  const hours = Math.floor(ms / (60 * 60 * 1000));
  const minutes = Math.floor((ms % (60 * 60 * 1000)) / (60 * 1000));

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m`;
  }
  return "< 1m";
}

/**
 * Record cooldown based on server response (seconds until retry)
 */
function recordCooldown(entityId: string, retryAfterSeconds: number): void {
  const key = getCooldownKey(entityId);
  const cooldownEnd = Date.now() + retryAfterSeconds * 1000;
  localStorage.setItem(key, cooldownEnd.toString());
}

/**
 * Clear cooldown for an entity
 */
function clearCooldown(entityId: string): void {
  const key = getCooldownKey(entityId);
  localStorage.removeItem(key);
}

/**
 * Check if error is a 429 rate limit error
 */
function isCooldownError(error: unknown): error is { response?: { status: number; headers?: Headers }; status?: number } {
  if (error && typeof error === "object") {
    // Axios-style error
    if ("response" in error && (error as { response?: { status?: number } }).response?.status === 429) {
      return true;
    }
    // Fetch-style error
    if ("status" in error && (error as { status?: number }).status === 429) {
      return true;
    }
  }
  return false;
}

/**
 * Extract retry-after seconds from error
 */
function getRetryAfterSeconds(error: unknown): number {
  // Default to 4 hours if we can't parse
  const defaultSeconds = 4 * 60 * 60;

  try {
    // Try to get from error message (e.g., "Try again in 3h 45m")
    if (error && typeof error === "object" && "response" in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response;
      const detail = response?.data?.detail;
      if (detail && typeof detail === "string") {
        // Parse "Try again in Xh Ym" format
        const match = detail.match(/(\d+)h\s*(\d+)m/);
        if (match) {
          const hours = parseInt(match[1], 10);
          const minutes = parseInt(match[2], 10);
          return hours * 3600 + minutes * 60;
        }
      }
    }
  } catch {
    // Ignore parse errors
  }

  return defaultSeconds;
}

/**
 * Button to refresh and enrich metadata for an entity.
 * Includes cooldown protection (4 hours) for regular users.
 * Admins bypass cooldown.
 */
export function RefreshMetadataButton({
  entityId,
  onRefresh,
  onEnrich,
  className,
  variant = "ghost",
  size = "sm",
}: RefreshMetadataButtonProps) {
  const { user } = useAuthStore();
  const isAdmin = user?.is_admin ?? false;

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [feedback, setFeedback] = useState<"success" | "error" | "cooldown" | null>(null);
  const [remainingCooldown, setRemainingCooldown] = useState(0);

  // Update cooldown timer
  const updateCooldown = useCallback(() => {
    if (isAdmin) {
      setRemainingCooldown(0);
      return;
    }
    setRemainingCooldown(getRemainingCooldown(entityId));
  }, [entityId, isAdmin]);

  // Check cooldown on mount and periodically
  useEffect(() => {
    updateCooldown();

    // Update every minute if on cooldown
    const interval = setInterval(updateCooldown, 60 * 1000);
    return () => clearInterval(interval);
  }, [updateCooldown]);

  const isOnCooldown = remainingCooldown > 0 && !isAdmin;
  const isLoading = isRefreshing;
  const isDisabled = isLoading || isOnCooldown;

  const handleClick = async () => {
    if (isDisabled) return;

    setIsRefreshing(true);
    setFeedback(null);

    try {
      // Refresh from source platform
      await onRefresh();

      // Enrich from external sources if available
      if (onEnrich) {
        await onEnrich();
      }

      // Clear any cached cooldown on success (server tracks the real cooldown)
      if (!isAdmin) {
        clearCooldown(entityId);
      }

      setFeedback("success");
      setTimeout(() => setFeedback(null), 2000);
    } catch (error) {
      // Handle 429 cooldown error from server
      if (isCooldownError(error)) {
        const retryAfter = getRetryAfterSeconds(error);
        recordCooldown(entityId, retryAfter);
        updateCooldown();
        setFeedback("cooldown");
        setTimeout(() => setFeedback(null), 3000);
      } else {
        setFeedback("error");
        setTimeout(() => setFeedback(null), 3000);
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  // Icon-only variant
  if (variant === "icon") {
    return (
      <button
        onClick={handleClick}
        disabled={isDisabled}
        title={
          isOnCooldown
            ? `Refresh available in ${formatRemainingTime(remainingCooldown)}`
            : feedback === "cooldown"
              ? "On cooldown"
              : "Refresh metadata"
        }
        className={clsx(
          "p-2 rounded-lg transition-all relative",
          "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          feedback === "success" && "text-emerald-400",
          (feedback === "error" || feedback === "cooldown") && "text-amber-400",
          className
        )}
      >
        <svg
          className={clsx("w-4 h-4", isLoading && "animate-spin")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          {isLoading ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          ) : feedback === "success" ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          ) : feedback === "error" ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          ) : feedback === "cooldown" ? (
            // Clock icon for cooldown
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          )}
        </svg>
      </button>
    );
  }

  // Button text based on state
  const getButtonText = () => {
    if (isLoading) return "Refreshing...";
    if (feedback === "success") return "Refreshed!";
    if (feedback === "error") return "Failed";
    if (feedback === "cooldown") return "On cooldown";
    if (isOnCooldown) return `Wait ${formatRemainingTime(remainingCooldown)}`;
    return "Refresh";
  };

  // Map variant to Button variant
  const buttonVariant = variant === "default" ? "primary" : variant;

  return (
    <Button
      variant={buttonVariant}
      size={size}
      onClick={handleClick}
      disabled={isDisabled}
      title={
        isOnCooldown
          ? `Refresh available in ${formatRemainingTime(remainingCooldown)}`
          : feedback === "cooldown"
            ? "This entity was recently refreshed"
            : undefined
      }
      className={clsx(
        feedback === "success" && "!text-emerald-400",
        feedback === "error" && "!text-red-400",
        feedback === "cooldown" && "!text-amber-400",
        isOnCooldown && "opacity-70",
        className
      )}
    >
      <svg
        className={clsx("w-4 h-4 mr-2", isLoading && "animate-spin")}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
      {getButtonText()}
    </Button>
  );
}

export default RefreshMetadataButton;
