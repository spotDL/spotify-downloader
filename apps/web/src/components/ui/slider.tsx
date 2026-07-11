import { forwardRef } from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "../../lib/utils";

interface TrackProps {
  values: number[];
  min: number;
  max: number;
  step: number;
  disabled?: boolean;
  onValueChange: (values: number[]) => void;
  className?: string;
  "aria-label"?: string;
}

/** Shared Radix track: segmented-flat, amber range, one thumb per value. */
function SliderTrack({ values, min, max, step, disabled, onValueChange, className }: TrackProps) {
  return (
    <SliderPrimitive.Root
      value={values}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      onValueChange={onValueChange}
      className={cn(
        "relative flex w-full touch-none select-none items-center",
        disabled && "opacity-50",
        className,
      )}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-elevated">
        <SliderPrimitive.Range className="absolute h-full bg-primary" />
      </SliderPrimitive.Track>
      {values.map((_, i) => (
        <SliderPrimitive.Thumb
          key={i}
          className={cn(
            "block size-4 rounded-full border border-primary bg-background shadow-sm",
            "transition-colors outline-none",
            "focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:pointer-events-none",
          )}
        />
      ))}
    </SliderPrimitive.Root>
  );
}

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
    ref,
  ) => {
    return (
      <div className={cn("w-full", className)}>
        {(label || showValue) && (
          <div className="mb-2 flex items-center justify-between">
            {label && (
              <label htmlFor={id} className="text-sm font-medium text-muted-foreground">
                {label}
              </label>
            )}
            {showValue && (
              <span className="font-mono tnum text-sm text-muted-foreground">
                {formatValue(value)}
              </span>
            )}
          </div>
        )}

        <SliderTrack
          values={[value]}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          onValueChange={([v]) => onChange(v)}
        />

        <input ref={ref} type="hidden" id={id} name={name} value={value} readOnly />

        <div className="mt-1 flex items-center justify-between">
          <span className="font-mono tnum text-xs text-faint">{formatValue(min)}</span>
          <span className="font-mono tnum text-xs text-faint">{formatValue(max)}</span>
        </div>
      </div>
    );
  },
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

  return (
    <div className={cn("w-full", className)}>
      {label && (
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">{label}</span>
          <span className="font-mono tnum text-sm text-muted-foreground">
            {formatValue(rangeMin)} – {formatValue(rangeMax)}
          </span>
        </div>
      )}

      <SliderTrack
        values={[rangeMin, rangeMax]}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onValueChange={(vals) => onChange([vals[0], vals[1]])}
      />
    </div>
  );
}
