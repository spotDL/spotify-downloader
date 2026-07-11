// A quiet flat hero surface. (Formerly a blurred cover-art backdrop; the
// Control Room system drops the blur/scale/grain look.) The `coverUrl` prop is
// retained for API compatibility. The caller supplies the positioned container
// and the z-indexed foreground content; this paints the token surface behind it.
export function HeroBackdrop({ coverUrl: _coverUrl }: { coverUrl?: string | null }) {
  return <div aria-hidden className="absolute inset-0 -z-10 bg-surface" />;
}
