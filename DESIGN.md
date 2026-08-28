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

**Press stock is the default; the negative is the companion.** The house style
is a cool neutral paper with near-black ink, and a true near-black canvas for
anyone who wants it. An explicit stored choice always wins; with none, the
operating system decides.

Two things were deliberately abandoned in the 2026 redesign.

The old light theme was a warm cream (`#F3F2ED`). The whole warm-neutral band
reads as paper/parchment and is the single most saturated default in generated
design; naming a token `--paper` does not make it a decision. The canvas is now
`#EAEBED`, a cool neutral at effectively zero chroma.

The old dark theme was navy-and-gold. Navy-and-gold is the first thing anyone
reaches for in finance, and terminal-dark is the second. The canvas is now a
true `#0A0B0D`, which reads as the printed negative of the light theme rather
than as a dashboard.

**Gilt survives, because it was earned.** `#F5B301` on the negative and
`#78581C` on press stock is the same signal at two exposures, and it stays on
data: headline figures, leverage bands, the sort indicator. It is never an
action.

**Action is ink, not colour.** Near-black fill with white text on press stock,
white fill with black text on the negative. A black button on paper is the most
emphatic control available and owes nothing to the SaaS blue.

| Token | Light | Dark | Role |
|---|---|---|---|
| `--bg` | `#EAEBED` | `#0A0B0D` | canvas |
| `--surface` | `#F6F7F8` | `#131519` | raised ground, bands |
| `--surface-sunken` | `#DCDEE2` | `#050608` | wells |
| `--ink` | `#0B0C0E` | `#F2F3F4` | primary text |
| `--ink-secondary` | `#434952` | `#A7ADB6` | secondary |
| `--ink-muted` | `#5B6068` | `#7F868F` | muted / missing |
| `--line` | `#C6C9CE` | `#2B2F36` | rule |
| `--line-strong` | `#8F949C` | `#4A505A` | structural rule |
| `--brand` / `--accent` | `#78581C` | `#F5B301` | gilt, data only |
| `--action` | `#111317` | `#F2F3F4` | the thing you press |
| `--link` | `#1A4FA0` | `#7FB0FF` | source / document links |

Every token is verified against the surface it actually sits on, not just
against `--bg`. `--ink-muted` and the shared amber both had to move when the
canvas got lighter: at the old values they measured 4.43:1 and 4.33:1 against
`#EAEBED`, under the AA floor, and the amber also failed on the sunken
surface. Tokens hold full colours (never use Tailwind opacity modifiers on
them); soft tints are their own variables.

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
gradients, colour blobs, glowing borders, coloured shadows, grain
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

The public half of that scale is now a set of classes rather than a table to retype:
`.ed-statement`, `.ed-title`, `.ed-section`, `.ed-sub`, `.ed-intro`, `.ed-body`,
`.ed-caption`. Each pairs size with the weight, tracking, leading and measure that size
needs, so a heading cannot be half-applied at a call site.

They exist because the middle of the scale was missing in practice. The homepage set its
section headings at 13px, **smaller than the 14px body they introduced**, and the other
public pages ran their own sizes: 14, 16, 18, 30 and 32px for the same job. Hierarchy was
inverted, not quiet. `.ed-section` is sans, not Charter: the serif stays reserved for
authored editorial, and a page of serif section heads reads as a magazine, which this
file rules out.

`SectionHeader` carries an `editorial` variant for public page titles. The public pages
were using `page`, which is the 22px application title, so /methodology and /how-to-use
opened smaller than the homepage's section headings.

## Wordmark

Text only: **Investment Intelligence**, with a smaller authorship line **by Nikolas
Savio**, composed (custom spacing/alignment), not typed into a navbar. No gradient logo,
sparkle, brain, candlestick, AI symbol, generic line-chart mark, or circular monogram. The
product name carries the identity.

## Layout grid

**Public:** max 1240px · 12 columns · outer margins 48–72 desktop, 28–40 tablet, 18–22
mobile · gutter 24 · reading column 5–7 columns. Do not centre everything. No narrow
column floating in a wide screen. No section wrapped in a background box by default.

`Container` is that grid as a component. Pages apply it **per section** rather than once
around everything, which is what lets a section opt out of the column: the deal-screen
band on the homepage runs the full width of the viewport while its contents stay on the
same grid lines as the sections above and below it. Section variety comes from surface
and width, not from a new decorative treatment per section.

`EditorialPage` is the layout for the public reading pages (methodology, how to use,
what's new). They were each a centred `max-w-3xl` column, which the paragraph above rules
out in as many words: at 1440px that left roughly 340px of dead margin either side of a
page whose argument is that it is dense and considered. The reading measure was the only
good reason for the narrow column and it is kept; the reclaimed width holds a title
column that stays with you down a long document.

**Application:** max workspace 1600px · left rail 200–220 · top utility bar 48–52 · main
padding 24–32 · tables use nearly all available width.

Headings, table labels, charts, source notes and side commentary share grid lines.

## Radius system

**Square by default.** Press stock is cut, not moulded. `DEFAULT`/`sm` are 0px;
2px is reserved for controls that should feel held. The old 3-6px scale was the
soft default every component library ships with, and at that size a radius
reads as timidity rather than as a decision. **No pill buttons.**
`rounded-circle` remains an explicit opt-in for genuinely round things.

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

## Glass materials

**Translucent glass is a primary surface style.** It is modelled on system
materials, not on a blurred card, and three things separate the two.

**Saturation.** A plain blur greys out what is behind it. The materials boost
saturation as they blur, which is why colour behind glass stays alive instead
of turning to fog. Every tier does `blur()` and `saturate()` together.

**A specular edge.** Glass is a sheet, so it catches light on the edge facing
the source and drops a shadow on the far side. The inset top highlight plus the
outer shadow are what make it read as a sheet lying ON the page rather than a
hole cut INTO it.

**It needs something behind it.** Glass over a flat field of one colour is
invisible. It goes on surfaces that genuinely float, and the canvas carries a
fixed, composited luminance layer at a few percent so the material has
something to refract.

| Tier | Blur | Use |
|---|---|---|
| `.glass-thin` | 10px | Full-width bands in normal flow |
| `.glass` | 20px | Panels and the search field |
| `.glass-chrome` | 20px | Headers, sidebars, sticky rails |
| `.glass-thick` | 32px | Drawers, menus, sheets, anything over live content |

### The rules that keep it readable

**Never on a data table.** Fifty rows of figures over a moving backdrop is
unreadable, and a `backdrop-filter` per row would be a compositing layer per
row. The workspace tables stay opaque.

**Tint opacity is set by contrast, not by taste.** The tiers are not equally
exposed: a band in normal flow only ever has the canvas behind it, while chrome
and drawers have live content passing underneath. At 0.72 a muted label over a
dark heading measured 3.05:1. Chrome and thick were raised to 0.84 and 0.93
(0.86 / 0.94 on the negative) until the pessimistic worst case, glass over
solid opposite-ink, clears AA on every ink that sits on them.

**The weakest ink is promoted off moving backdrops.** Inside `.glass-chrome`
and `.glass-thick`, `--ink-muted` resolves to `--ink-secondary`. Muted ink is
the first thing to disappear when the surface under it stops being a known
colour.

### Degradation

Three ways out, all of them opaque rather than unreadable: the OS
`prefers-reduced-transparency` setting, `@supports` for no `backdrop-filter`,
and print. Reduce Transparency is honoured because it exists for people who
genuinely cannot read translucent surfaces over moving content, and the house
style does not outrank that.

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

**Motion is a design system here, not a polish pass.** It is defined in
`app/motion.css` (tokens, reveal vocabulary) and `lib/motion.tsx` (runtime).
Nothing invents a duration or an easing at a call site.

### Tokens

Durations: `--dur-instant` 90ms · `--dur-fast` 160 · `--dur-standard` 260 ·
`--dur-slow` 420 · `--dur-cinematic` 720. Each step is roughly 1.6x the last.

Easing families: `--ease-responsive` (pointer feedback) · `--ease-smooth`
(directionless state) · `--ease-decelerate` (arriving) · `--ease-accelerate`
(leaving) · `--ease-expressive` (signature moments only).

### Springs

Five presets, generated from the damped-oscillator solution and sampled to CSS
`linear()`, so each has a real damping ratio and a real overshoot and runs on
the compositor rather than the main thread.

| Preset | ζ | Overshoot | Settle | Role |
|---|---|---|---|---|
| `tight` | 0.79 | 1.8% | 321ms | small controls under a finger |
| `responsive` | 0.84 | 0.8% | 500ms | general UI, nav indicator |
| `soft` | 0.92 | 0% | 579ms | panels, weighted blocks |
| `heavy` | 0.97 | 0% | 679ms | drawers and full sheets |
| `elastic` | 0.51 | 15.3% | 467ms | badges and small icons ONLY |

A tooltip does not move like a drawer. If two things of different mass share a
spring, one of them is wrong.

### Reveal vocabulary

Six ways to arrive, chosen by what is arriving, never one applied to
everything: `rule` (a drawn line, leads a section) · `wipe` (clip-path, for
images and tables, which are revealed rather than moved) · `rise` (supporting
prose) · `lift` (blocks with visual weight, on the soft spring) · `settle`
(figures, on the tight spring) · `line` (a line of type riding up inside its
own mask, no fade, so letters stay crisp).

### Choreography

Sequences are authored, not staggered by a uniform interval. The hero runs
rule → masked statement lines → search → supporting prose → secondary link,
because entrance order is the argument for importance. Stagger within a list is
capped at 480ms total so the last item never waits.

### Motion hierarchy

Ambient: none. Stillness is what makes the rest legible.
Micro: 90-160ms, spring-backed, on press and hover.
Section: 260-420ms, revealed once on approach.
Signature: the scroll-scrubbed coverage sequence, and the hero.

**Still banned:** parallax for its own sake, animated backgrounds, cursor
followers, pulsing buttons, continuous tickers, number-count animation,
scroll-jacking, and any reveal that re-fires when a section is scrolled back
into view.

**The workspace is deliberately quieter than the public pages.** Company
pages and the deal screen get micro-interactions and state motion only. An
analyst reading a table of figures is in a task, and choreography in front of
a number is an obstacle. This is the motion hierarchy applied, not an
oversight.

### Content is never gated behind motion

Visible is the base state in CSS. The hidden state is a class that JS adds and
then removes, so a crawler, a no-JS reader, a reduced-motion reader and a
headless renderer all get the finished page. Three independent paths end in
"visible": the observer, a two-frame entrance for anything already on screen,
and a 1.6s watchdog for the cases where neither `IntersectionObserver` nor
`requestAnimationFrame` runs. The first build of this system shipped a blank
homepage for exactly that reason.

### Reduced motion

`prefers-reduced-motion` collapses every spring to a plain curve, shortens the
long durations, and disables pointer displacement at the source: the magnetic,
tilt and scrub hooks read the query and never attach. State feedback (colour,
opacity, focus) survives, because removing it would make the interface harder
to follow rather than calmer.

## Controls

Primary: deep green fill, white text, 3px radius, 38–42px, no shadow, icon only if the
action needs one. Secondary: transparent, 1px rule border, ink text. Text action: blue or
green, underline on hover, clear focus. No pill buttons. Never two large CTAs side by side
in the homepage opening.

### Resting affordance

A control must be identifiable as a control **before** the pointer reaches it. Hover is a
confirmation, never the first disclosure: it does not exist on touch, it is invisible to
anyone scanning the page, and a surface whose controls only appear on contact reads as a
static document.

Every interactive element carries at least one of these at rest:

| Cue | Use for |
| --- | --- |
| Filled or bordered box | Primary and secondary actions, icon-only buttons, the theme switch |
| Link colour (`--link`) | Navigation in prose and in tables (tickers) |
| `.inspectable` dotted underline | A figure or a meta line that opens something. The financial-terminal convention for "there is more behind this" |
| A visible glyph (`.sortable-glyph`, `.disclosure-sign`) | Sort headers and collapsible group headers, which otherwise read as labels |

Two deliberate exceptions: the wordmark, which is a link home by convention and looks
wrong underlined, and disabled controls, where the absence of a cue is the message.

An icon on a bare background is a glyph, not a button. Give it a border.

Audit it, do not assume it. Query `button, a[href], [role=button]`, and for each check
resting background, border, underline, and link colour. The first run of this on the deal
screen returned 165 bare elements out of 223.

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
- Gradient text, side-stripe accent borders, coloured shadows
- An eyebrow label on every section; numbered markers where there is no real sequence
- Icon + heading + text cards repeated as the default section pattern
- Decorative candlesticks, tickers, terminals, trading-floor imagery
- Handwritten type, signature graphics, mascots, stock photography
