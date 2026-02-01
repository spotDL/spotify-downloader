import { useState, useEffect, useCallback } from "react";
import { clsx } from "clsx";
import { Button } from "./button";
import { useAuthStore } from "@/stores/auth";

// Cooldown duration in milliseconds (4 hours for regular users)
const COOLDOWN_MS = 4 * 60 * 60 * 1000;

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
 * Get the remaining cooldown time in milliseconds
 */
function getRemainingCooldown(entityId: string): number {
  const key = getCooldownKey(entityId);
  const lastRefresh = localStorage.getItem(key);
  if (!lastRefresh) return 0;

  const lastRefreshTime = parseInt(lastRefresh, 10);
  if (isNaN(lastRefreshTime)) return 0;

  const elapsed = Date.now() - lastRefreshTime;
  const remaining = COOLDOWN_MS - elapsed;
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
  return `${minutes}m`;
}

/**
 * Record a refresh action for cooldown tracking
 */
function recordRefresh(entityId: string): void {
  const key = getCooldownKey(entityId);
  localStorage.setItem(key, Date.now().toString());
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
  const [feedback, setFeedback] = useState<"success" | "error" | null>(null);
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

      // Record the refresh for cooldown tracking
      if (!isAdmin) {
        recordRefresh(entityId);
        updateCooldown();
      }

      setFeedback("success");
      setTimeout(() => setFeedback(null), 2000);
    } catch {
      setFeedback("error");
      setTimeout(() => setFeedback(null), 3000);
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
            : "Refresh metadata"
        }
        className={clsx(
          "p-2 rounded-lg transition-all relative",
          "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          feedback === "success" && "text-emerald-400",
          feedback === "error" && "text-red-400",
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
          : undefined
      }
      className={clsx(
        feedback === "success" && "!text-emerald-400",
        feedback === "error" && "!text-red-400",
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
