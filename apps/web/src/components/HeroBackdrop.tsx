import type { CSSProperties } from "react";

// The blurred cover-art hero backdrop + fade (mockup `.thero .bg` / `.fade`).
// Wraps the `.hero-backdrop`/`.hero-fade` token utilities: set `--hero-art` to
// the cover url so the palette layer paints and blurs it. Falls back to an
// accent conic gradient when no art is available. The caller supplies the
// positioned, `.grain` container and the z-indexed foreground content.

export function HeroBackdrop({ coverUrl }: { coverUrl?: string | null }) {
  const style = coverUrl
    ? ({ "--hero-art": `url("${coverUrl}")` } as CSSProperties)
    : undefined;
  return (
    <>
      {coverUrl ? (
        <div className="hero-backdrop" style={style} aria-hidden />
      ) : (
        <div
          aria-hidden
          className="absolute inset-x-[-10%] inset-y-0 top-[-30%] z-0 scale-[1.15] opacity-40 blur-[60px]"
          style={{
            background:
              "conic-gradient(from 210deg at 30% 20%, #123b2e, #0d2f3a, #1a1230, #123b2e)",
          }}
        />
      )}
      <div className="hero-fade" aria-hidden />
    </>
  );
}
