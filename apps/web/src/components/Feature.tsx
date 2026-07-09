import type { ReactNode } from "react";
import { type FeatureFlag, useFeature } from "../app/config";

// CONTRACT G — config-flag gate wrapper. Renders `children` only when the named
// `/config` feature flag is on; otherwise renders `fallback` (default nothing).
export function Feature({
  flag,
  children,
  fallback = null,
}: {
  flag: FeatureFlag;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  return <>{useFeature(flag) ? children : fallback}</>;
}
