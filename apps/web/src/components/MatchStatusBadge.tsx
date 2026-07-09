import { Badge } from "./Badge";

const STATUS_TONE = {
  auto: "neutral",
  community_verified: "brand",
  rejected: "danger",
} as const;

const STATUS_LABEL = {
  auto: "Auto",
  community_verified: "Verified",
  rejected: "Rejected",
} as const;

/** A match's status as a labelled badge. */
export function MatchStatusBadge({
  status,
}: {
  status: keyof typeof STATUS_LABEL;
}) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>;
}
