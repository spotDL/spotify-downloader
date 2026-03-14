/**
 * UI component prop types and display-related types.
 */

import type React from "react";

// ====== COVER ART ======
export type CoverArtSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "hero";
export type CoverArtShape = "rounded" | "circle";

export interface CoverArtProps {
  src: string | null;
  alt: string;
  size?: CoverArtSize;
  shape?: CoverArtShape;
  className?: string;
  fallbackIcon?: "artist" | "album" | "playlist" | "track";
  showPlayButton?: boolean;
  onPlay?: () => void;
}

// ====== MATCH SCORE GAUGE ======
export type ScoreLevel = "high" | "medium" | "low";

export interface MatchScoreGaugeProps {
  score: number; // 0-100
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animated?: boolean;
}

// ====== TOAST ======
export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

// ====== MODAL ======
export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: "sm" | "md" | "lg" | "xl";
  children: React.ReactNode;
}

// ====== NAVIGATION ======
export interface BreadcrumbItem {
  label: React.ReactNode;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
  adminOnly?: boolean;
}
