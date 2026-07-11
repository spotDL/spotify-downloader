import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Button as UIButton } from "./ui/button";

// The prominent page action (album/artist "Enqueue all", hero CTAs). A flat
// primary amber fill or a bordered ghost — distinct from the base `Button` so
// the hero treatment can be tuned without touching forms.
type Variant = "primary" | "ghost";

export function ActionButton({
  variant = "primary",
  icon,
  children,
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  icon?: ReactNode;
}) {
  return (
    <UIButton
      type={type}
      variant={variant === "ghost" ? "outline" : "primary"}
      className={className}
      {...props}
    >
      {icon}
      {children}
    </UIButton>
  );
}
