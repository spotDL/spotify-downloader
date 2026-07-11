# spotDL "Control Room" design system — apps/web build contract

Design rationale: `docs/superpowers/specs/2026-07-10-ui-redesign-design.md` (old repo checkout; the identity: broadcast-console precision — blue-ink surfaces, one phosphor-amber accent, segmented meters). This file is the working contract for UI code in **this** app.

## Monorepo ground rules (override everything else)

- **Never edit generated code:** `src/api/generated/**`, `src/api/ws-types.gen.ts`, `src/api/ws-protocol.gen.ts`, `src/routeTree.gen.ts`. CI (`make web-clients-check`) fails on drift. The only editable API files are `src/api/client.ts`, `src/api/ws-protocol.ts` and the non-generated glue.
- **Fonts are vendored** under `public/fonts/` and declared via `@font-face` — never a CDN `@import`. Control Room faces are already vendored: `SpaceGrotesk-Variable.woff2`, `IBMPlexSans-Variable.woff2`, `IBMPlexMono-{Regular,Medium,SemiBold}.woff2`.
- **One palette, two renderers:** every hex in `src/index.css` `@theme`/theme blocks MUST stay byte-identical to `apps/cli/src/spotdl_cli/tui/theme.py`. Change one → change both.
- **Themes:** `ThemeProvider` (`src/app/theme.tsx`) stamps `data-theme="dark"|"light"` on `<html>` from the `ui` store (`dark|light|system`) — keep that mechanism. Tokens flip via `[data-theme="light"]` overrides; the `@custom-variant dark` targets `[data-theme="dark"]`. Dark is default and must be pixel-perfect first; light must be fully usable (no dark-only hexes hardcoded in components).
- Lint is **oxlint** (`pnpm lint`); tests are colocated `*.test.tsx` with the MSW harness (`src/test/msw/*`, `render-app.tsx`). Keep tests green — update assertions to the new contract, never gut them.
- Feature gating (`<Feature>`, CONTRACT G), route guards, ConfigGate, auth/session/ui stores, ws reducer: behavior is untouchable. This is a reskin + layout rebuild, not a logic change.

## Tokens (defined in src/index.css — use ONLY these)

Tailwind classes: `bg-background`, `bg-surface`, `bg-card`, `bg-elevated`, `border-border`, `text-foreground`, `text-muted-foreground`, `text-faint`, `text-primary`/`bg-primary`/`text-primary-foreground`, `text-info`, `text-success`, `text-warning`, `text-destructive`, `ring-ring`, platform colors (`bg-spotify` etc. — identity dots/links only, never chrome).

Dark (default): background `#0b0d12`, surface `#12151c`, card `#171b24`, elevated `#1e2430`, border `#262d3a`, foreground `#e8eaf0`, muted-foreground `#8b93a7`, faint `#5a6274`, primary `#f5a623` (ink `#16110a`), info `#56c8d8`, success `#4ade80`, warning `#facc15`, destructive `#f4506c`.
Light: background `#f6f7f9`, card `#ffffff`, surface `#f0f1f4`, elevated `#e4e6eb`, border `#dde0e6`, foreground `#101318`, muted-foreground `#5c6474`, faint `#8a92a3`, primary `#c77e0a`, info `#0e7f92`, success `#15803d`, warning `#a16207`, destructive `#d92643`.

Type: `font-display` = Space Grotesk (headings; page titles `font-display text-2xl font-bold tracking-tight`), `font-sans` = IBM Plex Sans (body), `font-mono` = IBM Plex Mono + `tnum` utility class for ALL data (durations, counts, scores, ISRCs, dates, kbd). Eyebrow labels: `text-xs font-medium uppercase tracking-wider text-faint`.

## Non-negotiables (same as the original contract)

1. Tokens only — no zinc/emerald/slate/amber-500 Tailwind palette classes, no raw hexes in components, no `var(--…)` arbitrary values.
2. `cn()` from `src/lib/utils.ts` for class merging.
3. **The Meter** (`src/components/ui/meter.tsx`, with `scoreColor`) is the ONLY progress/score visualization. Replace `VuGauge` (radial) and `ProgressBar` internals with it. TUI mirrors with `▰▱`.
4. Flat surfaces: `bg-card border border-border rounded-lg`. Kill the maximalist layer: no `.grain`, `.glass`, `.hero-backdrop` blur heroes, `.hover-lift`, glow shadows, gradient text. `HeroBackdrop` becomes a quiet token-colored surface (keep the export/API).
5. Radius: `rounded-md` controls, `rounded-lg` cards. Icons: **lucide-react** only — delete `components/icons.tsx` usages by swapping to lucide equivalents (keep file exporting lucide re-exports if call sites are many).
6. Motion: `motion/react`, one page-enter fade/slide on route content roots, stagger ≤0.03s capped at 10; hover states are CSS. Respect the existing reduce-motion mechanism (`data-theme` hook + `prefers-reduced-motion`).
7. Feedback: `sonner` Toaster (mounted in `__root.tsx`); migrate `Toasts.tsx` store API to a shim over sonner (keep exports). Empty/error states: keep `EmptyState`/`ErrorState` APIs, restyle per contract (icon size-8 text-faint + sentence + one action; destructive alert names the failure + retry).
8. Copy: sentence case, buttons say what they do, no exclamation marks.
9. A11y floor: visible `focus-visible` ring (`ring-ring`), aria-labels on icon buttons, keyboard menus via Radix, 360px responsive, both themes legible.

## New dependencies (installed)

radix-ui primitives (`@radix-ui/react-dialog`, `dropdown-menu`, `tooltip`, `tabs`, `select`, `switch`, `slider`, `separator`, `scroll-area`, `avatar`, `popover`, `collapsible`, `progress`, `label`, `toggle-group`, `slot`, `alert-dialog`, `checkbox`), `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`, `motion`, `sonner`, `cmdk`.

## Component layout

- `src/components/ui/` (new, shadcn-style kebab-case): button, card, badge, input, label, textarea, select, switch, checkbox, slider, dialog, alert-dialog, dropdown-menu, popover, tooltip, tabs, collapsible, toggle-group, separator, scroll-area, avatar, alert, skeleton, progress, kbd, command, sonner, meter.
- Existing PascalCase components in `src/components/` keep their filenames and exported APIs (tests import them); rebuild their internals on the ui/ primitives.
- Shell: `layout/NavRail.tsx` → grouped sidebar (Discover / Library / System) with meter-bar wordmark; `layout/TopBar.tsx` → breadcrumb-less sticky bar with ⌘K trigger (`Kbd`), live queue pill (count + mini Meter from the ws store), theme toggle (cycles dark/light/system via the ui store); `layout/CommandPalette.tsx` → cmdk `CommandDialog`.

## Verify before commit

`pnpm -C apps/web lint && pnpm -C apps/web type-check && pnpm -C apps/web test && pnpm -C apps/web build` all green; `make web-clients-check` untouched-clean; screenshots of home/search/downloads in both themes.
