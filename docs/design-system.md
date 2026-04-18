# E-State — Design System

> Translation layer between [design-brief.md](design-brief.md) and the actual Tailwind + Shadcn implementation. Source of truth for tokens, component recipes, and status-badge colour logic. Enforced by the `e-state-design-tokens` rule.

## 1. Brand tone

From the brief: clean, minimal, modern, *trust-carrying*. The UI is a tool for high-stakes municipal decisions — it must feel official without feeling like a 2005 government portal. Warm sand blocks separate sections instead of harsh borders. Deep forest green leads the eye to decisive actions.

## 2. Colour tokens

Single source of truth lives in `apps/web/tailwind.config.ts` under `theme.extend.colors`. No other hex colours may appear in JSX or CSS.

```ts
export const colors = {
  // Brand
  forest:  { DEFAULT: "#3F5E3B", 600: "#365233", 700: "#2D4529" }, // Primary — actions
  olive:   { DEFAULT: "#B6B774", 700: "#9FA062" },                  // Accent — secondary
  sand:    { DEFAULT: "#E3C9A9", 300: "#EEDCC4" },                  // Background blocks
  rose:    { DEFAULT: "#C97A7F", 700: "#B06166" },                  // Alerts / critical

  // Surfaces
  surface: { DEFAULT: "#FFFFFF", muted: "#F7F6F2" },
  ink:     { DEFAULT: "#1F2421", muted: "#545B54" },                // Text

  // Semantic (derived, do not use raw hex in code)
  success: { DEFAULT: "#3F5E3B" }, // == forest
  warning: { DEFAULT: "#C79A3C" }, // amber, only for warning badges
  info:    { DEFAULT: "#4F6E8F" }, // cool slate, only for info badges
  danger:  { DEFAULT: "#C97A7F" }, // == rose
}
```

Usage map:

| Intent | Token | Example |
|---|---|---|
| Primary button | `bg-forest text-surface hover:bg-forest-700` | `Upload`, `Start Analysis`, `Resolve` |
| Secondary button | `bg-sand text-ink hover:bg-sand-300` | `Cancel`, `Filter` |
| Section block | `bg-sand-300` or `bg-surface-muted` | Dashboard cards, side panels |
| Critical badge | `bg-rose/10 text-rose-700 border-rose/30` | Row highlight in table |
| Warning badge | `bg-warning/15 text-[#8C6B1F] border-warning/30` | Yellow dots |
| Match badge | `bg-forest/10 text-forest-700 border-forest/30` | Clean rows |

## 3. Typography

- **Display + UI:** `Inter` variable, falling back to `Public Sans`, falling back to system `ui-sans-serif`. Loaded via `next/font`.
- **Numerals:** always tabular (`font-variant-numeric: tabular-nums`) inside tables, metric cards, and form inputs.
- **Scale** (Tailwind class / px / line-height):

| Token | Class | Size | Use |
|---|---|---|---|
| display | `text-4xl font-semibold tracking-tight` | 36 | Page titles |
| h1 | `text-2xl font-semibold` | 24 | Section headers |
| h2 | `text-xl font-medium` | 20 | Card titles |
| body | `text-base` | 16 | Default |
| small | `text-sm text-ink-muted` | 14 | Meta, captions |
| mono | `font-mono text-sm` | 14 | Tax IDs, cadastral numbers |

Ukrainian-specific: quotation marks rendered as `«…»`; thin non-breaking space between number and unit (`1 250 м²`).

## 4. Spacing and layout

- Base unit 4 px.
- Card padding: `p-6` desktop, `p-4` mobile.
- Grid gutter: `gap-6` desktop, `gap-3` mobile.
- Rounded corners (per brief): `rounded-lg` (8 px) for dense UI, `rounded-xl` (12 px) for hero cards and dialogs.
- Shadows: **one** depth token — `shadow-[0_1px_2px_rgba(31,36,33,0.06),0_8px_24px_rgba(31,36,33,0.04)]` exposed as `shadow-soft`. Nothing harder.

## 5. Components (Shadcn recipes)

Only Shadcn primitives; no ad-hoc custom tables or dialogs. The set:

| Primitive | Usage |
|---|---|
| `Button` | Variants `primary` (forest), `secondary` (sand), `ghost`, `destructive` (rose) |
| `Badge` | Status pill, see §6 |
| `Table` | All data grids; with sticky header on scroll |
| `Dialog` | Destructive confirmations, upload progress |
| `DropdownMenu` | Row actions |
| `Select`, `Combobox` | Filters |
| `Input`, `Label`, `Textarea` | Forms |
| `Tabs` | Back-office detail view (Overview / ДЗК / ДРРП / Visits) |
| `Sheet` | Inspector mobile bottom-sheet wizard |
| `Toast` | Non-blocking feedback |
| `Skeleton` | Loading states |

Prohibited: raw `<button>`, `<dialog>`, inline-styled divs acting as tables, `react-select`, `antd`, `MUI`. Icons come from `lucide-react` only.

## 6. Status badges

Every status in the system maps to exactly one badge:

| Status / severity | Label (uk) | Tone | Icon (lucide) |
|---|---|---|---|
| `severity:critical` | Критично | danger | `OctagonAlert` |
| `severity:warning` | Попередження | warning | `TriangleAlert` |
| `severity:info` | Інформаційно | info | `Info` |
| `status:open` | Відкрито | info | `Circle` |
| `status:in_review` | На перевірці | warning | `Clock` |
| `status:resolved` | Розв'язано | success | `CircleCheck` |
| `status:dismissed` | Відхилено | neutral | `CircleSlash` |
| citizen `synchronized` | Дані синхронізовано | success | `ShieldCheck` |
| citizen `needs_review` | Потребує уточнення | warning | `ShieldAlert` |
| citizen `in_progress` | Триває перевірка | info | `Hourglass` |

Rule: never communicate a status with colour alone — every badge has label + icon + tone.

## 7. Illustration & iconography

- Icons: `lucide-react` at stroke width 1.75, 20 px in tables, 24 px in hero sections.
- Empty-state illustrations: abstract line-art using forest + sand, 2-colour palette only. Commissioned SVGs live in `apps/web/public/illustrations/`.

## 8. Motion

- Micro-interactions use Tailwind `transition-colors` / `transition-transform` with `duration-200 ease-out`. Nothing bouncy.
- Inspector submission success uses a single 400 ms scale+fade ("satisfying but not silly").
- Respect `prefers-reduced-motion`.

## 9. Forbidden patterns (must-not-ship list)

Pulled from [.cursor/rules/web-design-quality.mdc](../.cursor/rules/web-design-quality.mdc) and adapted for E-State:

- Default Shadcn theme with no palette swap.
- Rainbow severity badges (red + orange + yellow + blue side by side).
- Dense tables without row hover and without keyboard navigation.
- Centered-gradient hero on any non-marketing screen.
- Uniform 16 px padding everywhere instead of designed rhythm.
- Raw hex in JSX/CSS.

## 10. Implementation checklist

- [ ] `apps/web/tailwind.config.ts` declares the token palette above.
- [ ] `apps/web/src/styles/globals.css` imports the Inter variable font via `next/font`.
- [ ] Shadcn components are installed via `pnpm dlx shadcn@latest add button badge table dialog dropdown-menu select input label textarea tabs sheet toast skeleton`.
- [ ] A Storybook-free `apps/web/src/app/(internal)/design` page renders every badge, button and metric card once, for visual regression eyeballing during the demo.
