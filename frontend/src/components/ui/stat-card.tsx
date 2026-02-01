import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface StatCardProps {
  /** Main value to display */
  value: string | number;
  /** Label describing the value */
  label: string;
  /** Optional trend indicator */
  trend?: {
    value: number;
    label?: string;
  };
  /** Icon to display */
  icon?: React.ReactNode;
  /** Color accent variant */
  variant?: "default" | "success" | "warning" | "error" | "info";
  /** Additional class names */
  className?: string;
}

const variantStyles = {
  default: {
    icon: "text-[var(--color-text-muted)]",
    value: "text-[var(--color-text-primary)]",
  },
  success: {
    icon: "text-[var(--accent-safe)]",
    value: "text-[var(--accent-safe)]",
  },
  warning: {
    icon: "text-[var(--accent-warm)]",
    value: "text-[var(--accent-warm)]",
  },
  error: {
    icon: "text-[var(--accent-peak)]",
    value: "text-[var(--accent-peak)]",
  },
  info: {
    icon: "text-[var(--accent-cool)]",
    value: "text-[var(--accent-cool)]",
  },
};

// Trend icons
const TrendUpIcon = () => (
  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
  </svg>
);

const TrendDownIcon = () => (
  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
  </svg>
);

export function StatCard({
  value,
  label,
  trend,
  icon,
  variant = "default",
  className,
}: StatCardProps) {
  const styles = variantStyles[variant];
  const isPositive = trend ? trend.value >= 0 : null;

  return (
    <div
      className={twMerge(
        clsx(
          "stat-card relative overflow-hidden",
          "bg-[var(--bg-panel)] border border-[var(--color-border-subtle)]",
          "rounded-2xl p-6",
          "transition-all duration-200",
          "hover:border-[var(--color-border)]"
        ),
        className
      )}
    >
      {/* Icon */}
      {icon && (
        <div className={clsx("mb-4", styles.icon)}>
          {icon}
        </div>
      )}

      {/* Value */}
      <div
        className={clsx(
          "stat-card-value text-3xl font-bold tracking-tight",
          styles.value
        )}
      >
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>

      {/* Label */}
      <div className="stat-card-label text-sm text-[var(--color-text-muted)] mt-1">
        {label}
      </div>

      {/* Trend */}
      {trend && (
        <div
          className={clsx(
            "stat-card-trend inline-flex items-center gap-1 mt-3",
            "px-2 py-0.5 rounded-full text-xs font-medium",
            isPositive
              ? "bg-[var(--accent-safe)]/10 text-[var(--accent-safe)]"
              : "bg-[var(--accent-peak)]/10 text-[var(--accent-peak)]"
          )}
        >
          {isPositive ? <TrendUpIcon /> : <TrendDownIcon />}
          <span>
            {isPositive ? "+" : ""}
            {trend.value}%
          </span>
          {trend.label && (
            <span className="text-[var(--color-text-dim)]">{trend.label}</span>
          )}
        </div>
      )}

      {/* Decorative gradient */}
      <div
        className={clsx(
          "absolute -right-8 -bottom-8 w-32 h-32 rounded-full opacity-5",
          variant === "success" && "bg-[var(--accent-safe)]",
          variant === "warning" && "bg-[var(--accent-warm)]",
          variant === "error" && "bg-[var(--accent-peak)]",
          variant === "info" && "bg-[var(--accent-cool)]",
          variant === "default" && "bg-white"
        )}
      />
    </div>
  );
}

/**
 * Grid layout for stat cards
 */
export interface StatCardGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
  className?: string;
}

export function StatCardGrid({
  children,
  columns = 4,
  className,
}: StatCardGridProps) {
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={twMerge(clsx("grid gap-4", gridCols[columns]), className)}>
      {children}
    </div>
  );
}

/**
 * Compact stat display for inline use
 */
export interface StatInlineProps {
  value: string | number;
  label: string;
  icon?: React.ReactNode;
  className?: string;
}

export function StatInline({ value, label, icon, className }: StatInlineProps) {
  return (
    <div className={twMerge("flex items-center gap-2", className)}>
      {icon && (
        <div className="text-[var(--color-text-muted)]">{icon}</div>
      )}
      <span className="font-semibold text-[var(--color-text-primary)]">
        {typeof value === "number" ? value.toLocaleString() : value}
      </span>
      <span className="text-sm text-[var(--color-text-muted)]">{label}</span>
    </div>
  );
}

export default StatCard;
