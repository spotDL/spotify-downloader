import type { ButtonHTMLAttributes, ReactNode } from "react";

// The maximalist hero action (mockup `.btn` / `.btn.ghost`): a primary emerald
// gradient with a lift-on-hover, or a bordered ghost. Distinct from the base
// `Button` (used by out-of-scope forms) so restyling the heroes doesn't ripple
// through login/settings/admin.

type Variant = "primary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary:
    "text-void bg-gradient-to-br from-emerald to-emerald-dim shadow-[0_8px_22px_-10px_var(--color-emerald)] hover:-translate-y-px",
  ghost:
    "text-ink-2 border border-line bg-transparent hover:bg-surface hover:text-fg",
};

export function ActionButton({
  variant = "primary",
  icon,
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  icon?: ReactNode;
}) {
  return (
    <button
      type={type}
      className={`hover-lift inline-flex items-center gap-2 rounded-[11px] px-4 py-2.5 text-sm font-semibold transition-transform disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
