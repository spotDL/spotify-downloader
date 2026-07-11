import { type HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export type SkeletonProps = HTMLAttributes<HTMLDivElement>;

/** Loading placeholder. Mirrors the shape of the content it stands in for. */
export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("animate-pulse rounded-md bg-elevated", className)} aria-hidden {...props} />
  );
}
