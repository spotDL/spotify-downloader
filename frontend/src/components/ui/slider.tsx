import { forwardRef, useState, useRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface SliderProps {
  /** Current value */
  value: number;
  /** Callback when value changes */
  onChange: (value: number) => void;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Label text */
  label?: string;
  /** Show value display */
  showValue?: boolean;
  /** Format function for displayed value */
  formatValue?: (value: number) => string;
  /** Whether the slider is disabled */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
  /** ID for form integration */
  id?: string;
  /** Name for form integration */
  name?: string;
}

export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      value,
      onChange,
      min = 0,
      max = 100,
      step = 1,
      label,
      showValue = true,
      formatValue = (v) => String(v),
      disabled = false,
      className,
      id,
      name,
    },
    ref
  ) => {
    const [isDragging, setIsDragging] = useState(false);
    const trackRef = useRef<HTMLDivElement>(null);

    // Calculate percentage for fill
    const percentage = ((value - min) / (max - min)) * 100;

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(parseFloat(e.target.value));
    };

    return (
      <div className={twMerge("w-full", className)}>
        {/* Label and value row */}
        {(label || showValue) && (
          <div className="flex items-center justify-between mb-2">
            {label && (
              <label
                htmlFor={id}
                className="text-sm font-medium text-[var(--color-text-secondary)]"
              >
                {label}
              </label>
            )}
            {showValue && (
              <span className="text-sm font-mono text-[var(--color-text-muted)]">
                {formatValue(value)}
              </span>
            )}
          </div>
        )}

        {/* Slider container */}
        <div className="relative" ref={trackRef}>
          {/* Custom track background */}
          <div
            className={clsx(
              "absolute inset-y-0 left-0 right-0 my-auto h-2 rounded-full",
              "bg-[var(--bg-surface)]"
            )}
          />

          {/* Fill track */}
          <div
            className={clsx(
              "absolute inset-y-0 left-0 my-auto h-2 rounded-full",
              "bg-gradient-to-r from-[var(--accent-safe)] to-[var(--accent-cool)]",
              "transition-[width] duration-75 ease-out"
            )}
            style={{ width: `${percentage}%` }}
          />

          {/* Native range input */}
          <input
            ref={ref}
            type="range"
            id={id}
            name={name}
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={handleInputChange}
            disabled={disabled}
            onMouseDown={() => setIsDragging(true)}
            onMouseUp={() => setIsDragging(false)}
            onTouchStart={() => setIsDragging(true)}
            onTouchEnd={() => setIsDragging(false)}
            className={clsx(
              "slider relative w-full h-2 appearance-none bg-transparent cursor-pointer",
              "focus:outline-none",
              disabled && "opacity-50 cursor-not-allowed",
              // Webkit thumb styling
              "[&::-webkit-slider-thumb]:appearance-none",
              "[&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4",
              "[&::-webkit-slider-thumb]:rounded-full",
              "[&::-webkit-slider-thumb]:bg-white",
              "[&::-webkit-slider-thumb]:shadow-lg",
              "[&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-150",
              "[&::-webkit-slider-thumb]:hover:scale-110",
              isDragging && "[&::-webkit-slider-thumb]:scale-110",
              // Firefox thumb styling
              "[&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4",
              "[&::-moz-range-thumb]:rounded-full",
              "[&::-moz-range-thumb]:bg-white",
              "[&::-moz-range-thumb]:border-none",
              "[&::-moz-range-thumb]:shadow-lg",
              "[&::-moz-range-thumb]:cursor-pointer"
            )}
          />
        </div>

        {/* Min/Max labels */}
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-[var(--color-text-dim)]">
            {formatValue(min)}
          </span>
          <span className="text-xs text-[var(--color-text-dim)]">
            {formatValue(max)}
          </span>
        </div>
      </div>
    );
  }
);

Slider.displayName = "Slider";

/**
 * Range slider with two thumbs for selecting a range
 */
export interface RangeSliderProps {
  /** Current range [min, max] */
  value: [number, number];
  /** Callback when range changes */
  onChange: (value: [number, number]) => void;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Label text */
  label?: string;
  /** Format function for displayed value */
  formatValue?: (value: number) => string;
  /** Whether the slider is disabled */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
}

export function RangeSlider({
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  formatValue = (v) => String(v),
  disabled = false,
  className,
}: RangeSliderProps) {
  const [rangeMin, rangeMax] = value;

  const minPercentage = ((rangeMin - min) / (max - min)) * 100;
  const maxPercentage = ((rangeMax - min) / (max - min)) * 100;

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newMin = Math.min(parseFloat(e.target.value), rangeMax - step);
    onChange([newMin, rangeMax]);
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newMax = Math.max(parseFloat(e.target.value), rangeMin + step);
    onChange([rangeMin, newMax]);
  };

  return (
    <div className={twMerge("w-full", className)}>
      {/* Label and value row */}
      {label && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-[var(--color-text-secondary)]">
            {label}
          </span>
          <span className="text-sm font-mono text-[var(--color-text-muted)]">
            {formatValue(rangeMin)} - {formatValue(rangeMax)}
          </span>
        </div>
      )}

      {/* Slider container */}
      <div className="relative h-2">
        {/* Track background */}
        <div className="absolute inset-0 rounded-full bg-[var(--bg-surface)]" />

        {/* Fill track */}
        <div
          className="absolute inset-y-0 rounded-full bg-gradient-to-r from-[var(--accent-safe)] to-[var(--accent-cool)]"
          style={{
            left: `${minPercentage}%`,
            right: `${100 - maxPercentage}%`,
          }}
        />

        {/* Min input */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={rangeMin}
          onChange={handleMinChange}
          disabled={disabled}
          className={clsx(
            "absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer",
            "pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto",
            "[&::-webkit-slider-thumb]:appearance-none",
            "[&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4",
            "[&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-white",
            "[&::-webkit-slider-thumb]:shadow-lg",
            disabled && "opacity-50"
          )}
        />

        {/* Max input */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={rangeMax}
          onChange={handleMaxChange}
          disabled={disabled}
          className={clsx(
            "absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer",
            "pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto",
            "[&::-webkit-slider-thumb]:appearance-none",
            "[&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4",
            "[&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-white",
            "[&::-webkit-slider-thumb]:shadow-lg",
            disabled && "opacity-50"
          )}
        />
      </div>
    </div>
  );
}

export default Slider;
