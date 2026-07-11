import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export type KbdProps = HTMLAttributes<HTMLElement>;

/** A keyboard-key hint, e.g. ⌘K. */
export const Kbd = forwardRef<HTMLElement, KbdProps>(({ className, ...props }, ref) => (
  <kbd
    ref={ref}
    className={cn(
      "inline-flex h-5 min-w-5 select-none items-center justify-center gap-0.5 rounded border border-border bg-surface px-1.5",
      "font-mono text-[0.6875rem] font-medium text-muted-foreground",
      className,
    )}
    {...props}
  />
));
Kbd.displayName = "Kbd";
