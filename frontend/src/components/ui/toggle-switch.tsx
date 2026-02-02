import { forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface ToggleSwitchProps {
  /** Whether the switch is on */
  checked: boolean;
  /** Callback when switch is toggled */
  onChange: (checked: boolean) => void;
  /** Label text */
  label?: string;
  /** Description text */
  description?: string;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Whether the switch is disabled */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
  /** ID for form integration */
  id?: string;
  /** Name for form integration */
  name?: string;
}

const sizeConfig = {
  sm: {
    track: "w-8 h-4",
    thumb: "w-3 h-3",
    translate: "translate-x-4",
    labelText: "text-sm",
  },
  md: {
    track: "w-11 h-6",
    thumb: "w-5 h-5",
    translate: "translate-x-5",
    labelText: "text-sm",
  },
  lg: {
    track: "w-14 h-7",
    thumb: "w-6 h-6",
    translate: "translate-x-7",
    labelText: "text-base",
  },
};

export const ToggleSwitch = forwardRef<HTMLInputElement, ToggleSwitchProps>(
  (
    {
      checked,
      onChange,
      label,
      description,
      size = "md",
      disabled = false,
      className,
      id,
      name,
    },
    ref
  ) => {
    const config = sizeConfig[size];

    const handleClick = (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        onChange(!checked);
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (!disabled) {
          onChange(!checked);
        }
      }
    };

    return (
      <label
        className={twMerge(
          clsx(
            "inline-flex items-start gap-3",
            disabled && "opacity-50 cursor-not-allowed",
            !disabled && "cursor-pointer"
          ),
          className
        )}
      >
        {/* Hidden input for form integration */}
        <input
          ref={ref}
          type="checkbox"
          id={id}
          name={name}
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
          aria-checked={checked}
        />

        {/* Track */}
        <div
          role="switch"
          aria-checked={checked}
          tabIndex={disabled ? -1 : 0}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
          className={clsx(
            "toggle-switch relative inline-flex flex-shrink-0 rounded-full",
            "transition-colors duration-200 ease-in-out",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-panel)]",
            config.track,
            checked
              ? "bg-[var(--accent-safe)]"
              : "bg-[var(--bg-surface)]"
          )}
        >
          {/* Thumb */}
          <span
            className={clsx(
              "toggle-switch-thumb pointer-events-none inline-block rounded-full",
              "bg-white shadow-lg",
              "transform transition-transform duration-200 ease-[var(--ease-spring)]",
              config.thumb,
              checked ? config.translate : "translate-x-0.5",
              "mt-0.5"
            )}
          />
        </div>

        {/* Label and description */}
        {(label || description) && (
          <div className="flex flex-col">
            {label && (
              <span
                className={clsx(
                  "font-medium text-[var(--color-text-primary)]",
                  config.labelText
                )}
              >
                {label}
              </span>
            )}
            {description && (
              <span className="text-xs text-[var(--color-text-muted)] mt-0.5">
                {description}
              </span>
            )}
          </div>
        )}
      </label>
    );
  }
);

ToggleSwitch.displayName = "ToggleSwitch";

export default ToggleSwitch;
