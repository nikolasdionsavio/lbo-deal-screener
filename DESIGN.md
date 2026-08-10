# Design

**Visual contract for every page.** If a change conflicts with this file, the file wins
or the file changes first.

## Concept: an annotated analyst workbook

Investment Intelligence is a financial research workbook, carefully edited for the web.
It combines the order of a well-built model, the source discipline of a filing review, the
reading quality of a research note, and the personal authorship of a tool one analyst
built and maintains.

A user should notice the **source discipline before any visual effect**. The design exists
to say: these figures can be checked.

It must feel: careful, informed, calm, precise, personal, sceptical of its own outputs.
It must not feel: corporate, futuristic, luxurious, playful, crypto, Bloomberg-imitating,
AI-branded, like a generic startup, like a component-library demo, or like a newspaper.

### Two densities, one identity

| | Public pages | Application |
|---|---|---|
| Pages | home, about, how it works, methodology, changelog, contact | overview, operations, financials, valuation, peers, LBO, score, memo, news |
| Feel | editorial, spacious, explanatory | compact, structured, data-led |
| Type | larger, wider measure | small, tight, tabular |
| Width | 1240px max | 1600px max workspace |

Same colours, type families, rules and link treatment across both. The public pages are
**not** forced into the app shell; the app is **not** a marketing page.

## Colour tokens

Light is the default. The palette is mostly neutral: the warm canvas carries the
character, colour carries meaning. Tokens hold full colours (never use Tailwind opacity
modifiers on them); soft tints are their own variables.

| Token | Light | Role |
|---|---|---|
| `--bg` | `#F3F2ED` | canvas |
| `--surface` | `#FCFBF7` | paper |
| `--surface-raised` | `#FFFFFF` | paper raised (fields, drawer) |
| `--surface-sunken` | `#EBEAE3` | wells |
| `--ink` | `#19201E` | primary text |
| `--ink-secondary` | `#59635F` | secondary text |
| `--ink-muted` | `#7A827F` | muted / missing |
| `--line` | `#D7D6CF` | rule |
| `--line-strong` | `#AEB4B0` | strong rule |
| `--brand` / `--accent` | `#215B52` | nav, selection, active research actions |
| `--brand-hover` | `#194A43` | |
| `--brand-soft` | `#E2ECE8` | faint selection wash |
| `--link` | `#315F82` | **source links and external documents only** |
| `--link-hover` | `#244A67` | |
| `--assumption` | `#8D6926` | **editable assumptions only** |
| `--assumption-soft` | `#F4EBD6` | editable cell background |
| `--negative` | `#A34738` | errors, material warnings, true negatives |
| `--negative-soft` | `#F5E5E1` | |
| `--positive-text` | `#3D6D51` | true positives |
| `--positive-soft` | `#E5EEE7` | |

**Colour rules.** Green = navigation, selection, active actions. Blue = source links.
Ochre = editable assumptions. Red = errors / material warnings / negative values where
colour adds meaning.

## Domain colours

The interface carries **five solid colours, one per data domain**, so that a figure's
colour tells you what kind of question it answers before you read the label. This is the
one place the palette is deliberately plural, and it is earned: these are the axes an
analyst actually sorts by.

| Role | Light | Dark | Domain |
|---|---|---|---|
| `--group-size` | `#3F5F7A` | `#8FB0CC` | scale: revenue, EBITDA, total assets |
| `--group-profit` | `#215B52` | `#7CB392` | profitability: gross, EBITDA, operating, net margin |
| `--group-balance` | `#8B6725` | `#C4A468` | leverage and balance sheet: net debt, cash, net debt / EBITDA |
| `--group-classify` | `#6B5A7D` | `#A999BD` | classification: sector, exchange, reporting period |
| `--group-quality` | `#7A5348` | `#C2988C` | disclosure and provenance: coverage, filing artifacts |

Each has a `-soft` tint (backgrounds, badges) and a `-rule` tint (column rules and
markers). All five clear WCAG AA as text on both canvases, 4.6:1 to 7.9:1 measured, so
they may carry labels and not only dots.

**The discipline is unchanged: colour encodes a domain, never decoration.** A hue is not
chosen because a section needed livening up. Do not invent a sixth. Within a domain,
value still comes from ink and weight; the hue marks the axis, it does not rank the
number. Red/green for direction (positive, negative, leverage bands) is separate and
still applies.

**Banned:** bright cyan, neon green, black terminal backgrounds, cream + terracotta,
gradients, colour blobs, frosted glass, glowing borders, coloured shadows, grain
overlays, fake paper textures. (Violet as a free-floating accent remains banned; the
muted `--group-classify` slate-purple above is permitted **only** as the classification
domain.)

## Typography roles

Three faces, three jobs. Never blur them.

- **Source Sans 3** (`font-sans`) — the interface: navigation, body, buttons, forms,
  tables, labels, help text, company descriptions.
- **Charter** (`font-display`) — authored editorial **only**: the homepage statement,
  Nikolas's notes, methodology introductions, memo titles, short observations.
  Charter is Matthew Carter's Bitstream face and is **not on Google Fonts**. The stack is
  `Charter, "Bitstream Charter", Charis SIL (webfont), Georgia, serif` — a locally
  installed Charter is used when present; Charis SIL (derived from Charter) is the served
  fallback. Not for every heading. No large italic pull-quotes.
- **Azeret Mono** (`font-mono`) — data **only**: tickers, dates, filing types, formula
  variables, source references, model assumptions, table values where fixed-width
  alignment helps, small technical metadata. Never paragraphs, buttons, or main nav.

**Banned faces:** Inter, Geist, Space Grotesk, Manrope, DM Sans, Playfair Display.
No oversized serif, no wide uppercase tracking.

### Scale

Public: statement 54–64 · page title 38–46 · section 25–30 · intro 19–21 · body 17–18 ·
caption 13–14 · technical label 11–12.

Application: company title 26–30 · section 18–21 · body 14 · table 13 · table heading
11–12 · metadata 11.

Tabular numerals on all financial data. Max measure ~68ch for long copy. Do not make every
heading bold: build hierarchy with size, spacing and position.

## Wordmark

Text only: **Investment Intelligence**, with a smaller authorship line **by Nikolas
Savio**, composed (custom spacing/alignment), not typed into a navbar. No gradient logo,
sparkle, brain, candlestick, AI symbol, generic line-chart mark, or circular monogram. The
product name carries the identity.

## Layout grid

**Public:** max 1240px · 12 columns · outer margins 48–72 desktop, 28–40 tablet, 18–22
mobile · gutter 24 · reading column 5–7 columns. Do not centre everything. No narrow
column floating in a wide screen. No section wrapped in a background box by default.

**Application:** max workspace 1600px · left rail 200–220 · top utility bar 48–52 · main
padding 24–32 · tables use nearly all available width.

Headings, table labels, charts, source notes and side commentary share grid lines.

## Radius system

Controls 3px · search field 4px · drawers/menus 6px · chart/image frames 6px.
Nothing larger as a general pattern. **No pill buttons.** Tailwind radii are capped at 6px
so untouched components inherit the discipline.

`rounded-full` is capped at 6px too. It was the one key left uncapped, so it fell through
to Tailwind's 9999px and twenty-four pills accumulated behind the rule that bans them.
Genuinely circular shapes (status dots, avatars) use **`rounded-circle`**, which is an
explicit opt-in rather than an unnoticed default.

## Surfaces and shadows

Most information sits **directly on the page**. Use thin rules, alignment, small surface
shifts, section labels and controlled spacing instead of containers. Shadows only for
things that sit above the page (menu, tooltip, drawer, modal) via `--shadow-pop`.
`--shadow-card` is `none`. Count the rounded containers; delete any that do not need a
separate interaction boundary.

`Card` enforces this rather than leaving it to memory. Its default `section` variant is a
top rule plus spacing, so a block of figures sits on the page; `variant="panel"` restores
the bordered surface and is reserved for content that really is its own interaction
surface, such as a sign-in form. The component previously drew a bordered, filled, rounded
box at all 52 call sites, which is most of why the app sat near 2:1 rules to boxes rather
than the 10:1 below.

## Rules, not boxes (the governing device)

Measured from Vitsœ's live stylesheet: **138 single-edge hairlines against 14 four-sided
borders — roughly 10:1** — and their most-used colour is the hairline grey itself, used
more than white or black. Structure comes from *ruling*, not carding.

Our equivalent: `--line` is the most-used token in the system. Target ~10:1 rules to
containers. Radius 0–6px. No card shadows. Before adding a container, try a rule.

Also adopted from Vitsœ: a **20px baseline**, all spacing a multiple of 4; a small closed
type scale (roughly six sizes per density); letter-spacing left `normal` (only large
display numerals may go slightly negative).

## Table rules

Tables are the most polished part of the product. Real semantic `<table>` markup, real
`<th scope>`, headers associated with cells, accessible name via `aria-label`.

**Density ladder (Carbon, verbatim):** 24 / 32 / 40 / 48 / 64px. Editorial tables sit at
48; the workspace at 32; dense statements may use 24. **Chrome height is slaved to row
height** — a small toolbar only with sm/xs rows, a tall toolbar only with lg/xl. That one
rule is what makes two densities read as designed rather than zoomed.

**Type (Carbon):** column header **14px / 600** over row text **14px / 400** — the *same
size*, separated only by weight. Resting row text sits at `--ink-secondary` and **promotes
to `--ink` on hover**. Column spacing 16px; sort icon gap 8px.

- Plain paper background · thin horizontal rules · minimal vertical rules
- Sticky first column · sticky period headings
- Line items left, **numbers right, tabular numerals** (Carbon gives no alignment rule;
  this is ours and it is not optional for financial data)
- Negatives in parentheses · consistent precision
- Blank/unavailable shown with specific text, never a bare dash
- Stronger rule between statement sections
- First column 240–300px · period column 104–124px
- Sorting: three states, `aria-sort` bound, **unsorted icons appear on hover/focus only**;
  `Tab` to header, `Space`/`Enter` to sort
- Long column titles wrap to two lines, then truncate, with the full text in a tooltip
- Expandable rows for supplementary detail or data that needs an extra query
- Loading uses **skeleton rows, never spinners**
- Hover reveals available source actions

### Every number ships with a backlink

BamSEC's discipline, and the reason this design is called *annotated*: a figure is never
displayed without a route to where it came from. The annotation layer is a first-class,
addressable object — not a tooltip. Tables link to the exact table in the filing; the
source record is openable from any value; a company's saved source records collect in one
place. If a number cannot be traced, it is marked `M` and says why.

### Source-state treatments

Markers (never colour or letter alone; always an accessible label + tooltip):

| Marker | Meaning | Treatment |
|---|---|---|
| `F` | filed | normal ink |
| `C` | calculated | subtle dotted underline |
| `A` | assumption | pale ochre cell background |
| `M` | missing / unmapped | muted text + specific reason |

Clicking a value opens the **source drawer** (right side): metric, displayed value,
classification, formula, inputs, fiscal period, filing type, filing date, original line
item, original unit, direct filing link, mapping limitation. Narrow label column, wider
value column, sections separated by rules, not cards. Fixed label at top: **Source
record**. Never "AI explanation", "smart insight", "confidence score".

## Chart rules

Charts are figures from a research note. Structure, always:

```
Question or chart title
Small explanatory subtitle
Chart
Figure caption
Source and calculation note
```

Plain background · one highlighted series (`--accent`) · muted comparisons (`#9AA39F`,
`#C0C5C2`) · negatives `--negative` · assumptions/sensitivity `--assumption` · direct
labels · visible units · restrained gridlines · tabular numerals · consistent dimensions.

**Banned:** rainbow palettes, gradient areas, self-drawing line animation, 3D, floating
rounded chart cards. Every chart answers one stated question.

## Motion rules

Fast state 100ms · standard 150ms · drawer/panel 180–220ms. Motion only for: search
results opening, source drawer, row selection, assumption updates, navigation, loading
completion.

**Banned:** scroll entrance animations, staggered reveals, parallax, floating elements,
animated backgrounds, cursor effects, pulsing buttons, continuous tickers, spring motion,
number-count animations. `prefers-reduced-motion` is honoured everywhere.

## Controls

Primary: deep green fill, white text, 3px radius, 38–42px, no shadow, icon only if the
action needs one. Secondary: transparent, 1px rule border, ink text. Text action: blue or
green, underline on hover, clear focus. No pill buttons. Never two large CTAs side by side
in the homepage opening.

## Icons

Only where a standard symbol aids recognition: search, open source, download, save, close,
filter, sort, expand, external link. 14–16px, one stroke weight. No icons in coloured
boxes, no icons on section headings. **Banned:** sparkles, stars, brains, robots, magic
wands, rockets, lightning bolts, abstract finance symbols.

## Empty and loading states

Factual, no illustrations, no cheerful marketing copy:

> **No peer data available**
> Comparable-company data could not be mapped reliably for this company.

Loading retains page structure (table skeleton rows, chart frames) with specific status
text ("Retrieving filings", "Mapping reported line items", "Calculating valuation
metrics"). Never invent a stage the backend does not actually expose.

## Accessibility

WCAG AA. Body ≥4.5:1 both themes. Real table semantics with associated headers. Keyboard
navigation and visible focus everywhere. `prefers-reduced-motion` honoured. **Colour is
never the only carrier of meaning**: filed/calculated/assumption/missing/warning each have
text or shape in addition to colour.

## Approved / rejected

**Approved**
- An aligned information strip with direct labels and a clickable source line under it
- A financial table with sticky first column, F/C/A/M markers and a source drawer
- A chart with a question title, caption and source note
- A model input sheet: assumption · current value · source · editable field · reset
- The deal score as a methodology table with a large plain total
- "Nikolas's note": thin left rule, Charter body, small authorship label
- A dated changelog of real changes

**Rejected**
- A row of oversized KPI cards; each metric in its own card
- A circular score gauge, speedometer, ring chart, star rating, glowing number
- Gradient text, glassmorphism, side-stripe accent borders, coloured shadows
- An eyebrow label on every section; numbered markers where there is no real sequence
- Icon + heading + text cards repeated as the default section pattern
- Decorative candlesticks, tickers, terminals, trading-floor imagery
- Handwritten type, signature graphics, mascots, stock photography
