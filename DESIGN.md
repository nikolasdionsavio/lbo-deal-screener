# Design

Refined institutional. A fund's internal research tool executed with care: quiet
surfaces, document-grade typography, dense scannable numbers, one disciplined accent.
Light is the default; dark is a first-class equal. The sidebar stays deep navy in both
themes (constant brand anchor).

## Theme

Semantic CSS variables on `:root` (light) and `.dark` (dark), consumed by Tailwind.
Class strategy (`darkMode: "class"`), toggled on `<html>`, persisted in
`localStorage("theme")`, system preference as the default, no-flash inline script in the
document head.

### Light

- `--bg` #f5f6f8 (cool neutral, chroma toward navy, never cream)
- `--surface` #ffffff · `--surface-sunken` #eef0f4 (inputs, wells, chart plot bg)
- `--ink` #0f172a · `--ink-secondary` #3f4c63 · `--ink-muted` #5b6779 (≥4.5:1 on surface)
- `--line` rgba(15,23,42,0.08) · `--line-strong` rgba(15,23,42,0.16)
- `--brand` #1e3a5f · `--brand-hover` #16304f · `--brand-soft` rgba(30,58,95,0.07)
- `--accent` #0d9488 (graphics/large only) · `--positive-text` #0f766e (4.5:1 small text)
- `--negative` #b91c1c · `--negative-text` #b91c1c
- `--warn` #b45309 (icons/badges) · `--warn-text` #92400e · `--warn-soft` rgba(180,83,9,0.09)
- Sidebar: #16273e → #122033 gradient-free solid is fine; active item rgba(255,255,255,0.10)

### Dark

- `--bg` #0b1322 · `--surface` #121c30 · `--surface-sunken` #0d1626
- `--ink` #e7ebf3 · `--ink-secondary` #b6c0d0 · `--ink-muted` #8e99ac
- `--line` rgba(231,235,243,0.08) · `--line-strong` rgba(231,235,243,0.16)
- `--brand` #466a96 (interactive navy, readable on dark) · `--brand-hover` #5379a8 ·
  `--brand-soft` rgba(120,160,205,0.12)
- `--accent` #14b8a6 · `--positive-text` #2dd4bf · `--negative-text` #f87171 ·
  `--warn-text` #fbbf24 · `--warn-soft` rgba(251,191,36,0.10)
- Sidebar: #0a111e (one step darker than bg for layering)

Charts, badges, and the TradingView widget (`theme` prop, re-mounted on toggle) all read
the active theme. No hardcoded slate-*/white classes anywhere data-bearing; everything
flows through tokens.

## Typography

- **Body/UI/data: Inter** (next/font), 14px base UI, 13px dense tables, tabular-nums on
  every numeric, right-aligned numeric columns.
- **Display: Source Serif 4** (next/font) — ONLY for: landing hero, the company-name
  header, page h1 titles, and memo section headings (document character). Never labels,
  buttons, table content, or stats.
- Fixed rem scale: 0.75 / 0.8125 / 0.875 / 1 / 1.125 / 1.375 / 1.75 / 2.125. Weight
  contrast 400–600; numbers may use 550 via font-variation where helpful.
- `text-wrap: balance` on headings; prose capped ~70ch.

## Depth & Surfaces

- Card = `--surface` + 1px `--line` border + `0 1px 2px rgba(15,23,42,0.04)`. Hoverable
  cards raise to `0 2px 8px rgba(15,23,42,0.07)` + `--line-strong` over 150ms.
- No glassmorphism, no gradients on surfaces, no side-stripe accents.
- Radius scale: 6px controls, 10px cards, 999px pills. Consistent.

## Components

- Buttons: primary = brand fill (hover brand-hover, active translate-y-px, disabled 45%
  opacity, focus-visible 2px accent ring offset 2). Secondary = surface + line border.
  Destructive = negative outline until hover.
- Inputs: `--surface-sunken` bg, 1px line border, focus border brand + ring
  `--brand-soft`; invalid = negative border + helper text.
- Tables: 12px medium muted header row (no wide tracking), row hover `--brand-soft`,
  1px `--line` dividers, numeric cells tabular right-aligned.
- Badges/ratings: tinted soft backgrounds with readable-text tokens, never solid neon.
- Skeletons: `--surface-sunken` shimmer 1.2s linear, honoring reduced motion.
- Empty/degraded states: one sentence of explanation + the source/why, styled as
  designed content (muted ink, not red).

## Charts (Recharts)

- Series palette: brand, accent, `--ink-muted`, plus `--negative` only for true
  negatives. Grid `--line`, axes 11px `--ink-muted`, no vertical gridlines on bar
  charts. Shared tooltip style: `--surface` bg, `--line-strong` border, 10px radius,
  12px text, currency/percent formatted exactly like the tables.
- Sensitivity matrices keep the green↔red cell tinting (meaningful color), tuned per
  theme so text stays ≥4.5:1.

## Motion

- 150–200ms, ease-out (cubic-bezier(0.16,1,0.3,1)) for hover/focus/expand; 250ms for
  theme cross-fade on `background-color`/`color` only.
- No page-load choreography. `@media (prefers-reduced-motion: reduce)` zeroes durations.

## Iconography

Inline SVG, 1.5px stroke, 16/20px grid (theme toggle, external-link, form badges). No
icon font, no emoji.

## Aesthetic v2 (2026-06-12, reference-driven)

User-chosen references: Framer "Fluence" and "Sanjaya" templates. Shared language to
adopt, translated to the product register (identity stays navy/teal for data semantics;
the references contribute geometry, surfaces, and chrome):

- **Light sidebar (both themes follow surface logic now, navy retired):** sidebar =
  `--bg` tone with a hairline right border; brand block top (wordmark + one-line
  descriptor, dashed divider below); nav items get 16px inline 1.5px-stroke icons;
  the ACTIVE item is a raised card (surface bg + line border + card shadow, 8px
  radius) — Sanjaya's pattern; inactive items are quiet ink-muted with a soft hover.
  Dark theme: same structure on dark tokens.
- **Dashed hairline language:** section dividers (landing, dashboard between major
  sections, memo between sections, sidebar blocks) use 1px dashed `--line-strong`
  rules. Solid hairlines remain inside tables/cards.
- **Pill geometry:** primary buttons become ink-filled pills (`--ink` bg, surface
  text, rounded-full, Fluence's "Contact" button); secondary = surface pill with line
  border. Chips/badges stay pills. Controls keep 8px radius; cards go 14px.
- **Hero (landing only):** Fluence-style rounded container (`--surface-sunken`, 24px
  radius, generous padding) holding the serif headline, an outlined capsule label
  ("DEAL SCREENING", one deliberate use, landing only), and the search styled as a
  large prompt box (white card, 16px radius, shadow, sample-ticker chips INSIDE the
  box footer, ink pill submit affordance).
- **Tile rows (Sanjaya "My Stack"):** landing's Screen/Model/Memo points become
  icon-tile rows (28px rounded-square tile + name + one-line sub), and the dashboard
  Data section adopts the same tile treatment for source rows.
- **Motion:** landing gets one gentle fade/6px-rise reveal per section (IntersectionObserver,
  280ms ease-out, content visible by default for no-JS/reduced-motion); app pages keep
  hover/focus transitions only.
- Whitespace scale up one notch on page paddings (24→32 content gutters); body bg
  stays `--bg` cool off-white; no violet adoption — the references' airiness comes
  from surfaces and geometry, not their accent hue.
