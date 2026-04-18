# E-State — User Flows

> Concrete step-by-step flows mapped to screens from [design-brief.md](design-brief.md). Source of truth for route layout in `apps/web`, navigation, and state transitions. Each screen references the API endpoints defined in [api-contract.md](api-contract.md).

## 1. Personas

| Persona | Role | Primary device | Access |
|---|---|---|---|
| Землевпорядник | Staff — back-office analyst | Desktop | JWT, full access |
| Інспектор | Staff — field auditor | Mobile phone | JWT scoped to assigned findings |
| Мешканець | Citizen | Mixed (often mobile) | Unauthenticated + CAPTCHA |
| Голова ОТГ / Депутат | Staff — read-only | Desktop | JWT, read-only on `/reports/*` |

## 2. End-to-end happy path

```mermaid
sequenceDiagram
  actor Z as Землевпорядник
  actor I as Інспектор
  actor C as Мешканець
  participant W as Web
  participant A as API

  Z->>W: Upload ДЗК + ДРРП
  W->>A: POST /upload
  W->>A: POST /matcher/run
  W-->>Z: Dashboard with stats
  Z->>W: Filter severity=critical
  Z->>W: Open finding detail
  Z->>W: Assign to Інспектор
  I->>W: Open mobile "My visits"
  I->>W: Open finding, take photos
  W->>A: POST /inspector/photos/presign
  W->>A: POST /inspector/visits
  W-->>I: Resolved ✓
  C->>W: Citizen lookup by РНОКПП
  W->>A: POST /citizen/lookup
  W-->>C: Status: synchronized
```

## 3. Back-office flow (Землевпорядник)

Routes under `apps/web/src/app/(back-office)/`.

### 3.1 `/` — Dashboard

From [design-brief.md §1](design-brief.md#1-main-dashboard-e-state).

- **Header:** title `E-state`, subtitle `Система виявлення розбіжностей активів ОТГ`.
- **Metrics row:** `Total Records`, `Mismatches Found`, `Files Processed` — pulled from `GET /reports/summary` (not in contract yet; returns counts across all datasets).
- **Primary CTA:** large "Завантажити дані" button → navigates to `/upload`.
- **Recent datasets:** table of the last 10 `dataset` rows with status pill and row counts.

### 3.2 `/upload`

From [design-brief.md §2](design-brief.md#2-upload-interface).

- Drop zone accepting two files (`.xlsx`, `.csv`). Both required before CTA enables.
- Client-side validation: file type + size (< 25 MB each).
- "Почати аналіз" → `POST /upload`, then `POST /matcher/run`, then navigate to `/datasets/:id/findings`.
- Visual states: `Idle → Uploading → Queued → Running matcher → Ready`.

### 3.3 `/datasets/:id/findings`

From [design-brief.md §3](design-brief.md#3-analysis-results-the-workhorse-view).

- **Summary tier:** three Shadcn cards: `Критичні`, `Попередження`, `Інформаційні`.
- **Filters:** severity chips, `finding_type` multiselect, `koatuu` input, free-text person search (debounced 300 ms).
- **Data table:** columns `Особа (masked)`, `Тип розбіжності`, `Severity`, `Locality (koatuu)`, `Виявлено`, `Статус`, `Дії`.
- Status badges map to the design palette per [design-system.md](design-system.md).
- Row click → `/datasets/:id/findings/:findingId`.
- Row actions: `Призначити інспектору`, `Відхилити`.

### 3.4 `/datasets/:id/findings/:findingId`

From [design-brief.md §4](design-brief.md#4-record-details-deep-dive).

- **Header:** finding type, severity badge, person full name, `Призначити інспектору` button.
- **Split-screen:** left card `ДЗК` (all the person's `land_parcel` rows for this dataset), right card `ДРРП` (all `real_estate` rows). Divergent fields auto-highlighted using the rose tone from the palette.
- **Finding computed metrics:** plain-language explanation per detector, e.g. for `AREA_PORTFOLIO_DELTA`:
  > Сумарна площа нерухомості (6 989.7 м²) у 7.7 раз перевищує площу земельних ділянок (903 м²).
- **Visits timeline:** chronological list of `FieldVisit` entries.
- **Actions row:** `Resolve manually`, `Dismiss` (with reason), `Assign to inspector`.

### 3.5 `/datasets/:id/reports`

- KPI strip: `Очікуване зростання податкових надходжень`, `Резолюції інспекторів`, `% red→green`.
- Budget-impact chart (Recharts) from `GET /reports/budget-impact`.
- Export button: CSV of the current `findings` filtered view.

## 4. Inspector flow (Інспектор)

Routes under `apps/web/src/app/(inspector)/`, mobile-first. Every page is usable on a 360 px screen with one-handed navigation.

### 4.1 `/inspector` — Assigned visits

- List of findings assigned to the current inspector, sorted by severity → koatuu → distance (if GPS allowed).
- Sticky filter: `Сьогодні`, `Цього тижня`, `Усі`.
- Each card: severity stripe, person name, object type hint, КОАТУУ, address fragment.

### 4.2 `/inspector/finding/:id`

- Read-only finding summary (same explanation as back-office).
- Two-column ДЗК vs ДРРП collapsed by default into an accordion on mobile.
- **Primary CTA:** `Розпочати огляд`.

### 4.3 `/inspector/finding/:id/visit`

Bottom-sheet form, five steps, each 1 fingerprint tall:

1. **Фактичний тип об'єкта** — Shadcn `RadioGroup` with the object-type taxonomy + "інше" free-text.
2. **Фактична площа, м²** — numeric input with keypad.
3. **Фактичне використання** — select `Житлове | Комерційне | Господарське | Не використовується | Інше`.
4. **Фото** — opens camera; uploads via presigned URL. Min 1 photo, max 5.
5. **Нотатки + GPS** — free-text + "Прив'язати геолокацію" toggle.

On submit: `POST /inspector/visits`. Success screen: `Готово — Розбіжність розв'язано`. The finding jumps to `resolved` state across the system.

## 5. Citizen flow (Мешканець)

Routes under `apps/web/src/app/(citizen)/`. Public, unauthenticated.

### 5.1 `/citizen`

- Hero with the product promise in citizen-friendly Ukrainian: `Перевірте, чи ваші записи в реєстрах ОТГ актуальні`.
- Explains the law basis and the ОТГ's right to audit (links to [legal-compliance.md](legal-compliance.md) excerpts on a dedicated `/legal` page).
- CTA: `Перевірити за РНОКПП`.

### 5.2 `/citizen/lookup`

- Single form: РНОКПП input (client-side masked while typing), CAPTCHA widget (hCaptcha or Cloudflare Turnstile), submit.
- Result page shows **only** masked tax ID, full name, record counts, and a status badge:
  - `Дані синхронізовано` (green) — no open findings for this person.
  - `Потребує уточнення` (warning) — ≥ 1 open finding on the person; shows citizen-safe summary sentences, never citing neighbours.
  - `Триває перевірка` (info) — a finding is assigned to an inspector.
- Link: `Як оновити дані` — clear instructions to visit ЦНАП or file online, with specific templates.

## 6. State transitions

```mermaid
stateDiagram-v2
  [*] --> open: Matcher creates finding
  open --> in_review: Staff assigns to inspector
  in_review --> resolved: Inspector submits FieldVisit
  open --> resolved: Staff resolves manually
  open --> dismissed: Staff dismisses with reason
  in_review --> dismissed: Staff dismisses mid-review
  dismissed --> open: Reopen (admin only, within 14 days)
  resolved --> open: Reopen (admin only, within 14 days)
```

## 7. Empty and error states (mandatory)

Every list-backed screen renders explicit states rather than blank space:

| State | What to render |
|---|---|
| Empty (no data) | Illustration + CTA to upload / assign |
| Loading | Skeleton rows, never a spinner-on-blank |
| Error | Message with correlation ID + "Повторити" button |
| Forbidden | Clear explanation of why, link to legal page |

## 8. Accessibility baseline

- All interactive elements reachable by keyboard.
- Visible focus ring matching the primary color at reduced opacity.
- Status is never communicated by colour alone — every badge has a text label and icon.
- Minimum body text 16 px; tables allow horizontal scroll instead of truncation on narrow screens.
