# E-State — Pitch & MVP Overview

> **Прозорість у кожному квадратному метрі.**
> A GovTech SaaS that automates asset audits for Ukrainian ОТГ (united territorial communities) by cross-checking the **ДЗК** (land cadaster) and **ДРРП** (real-estate registry).

---

## 1. The Problem

In Ukrainian **ОТГ (united territorial communities)**, there is a systemic mismatch between:

- what is **written in official registries** (ДЗК — land, ДРРП — real estate), and
- what is **actually on the ground**.

A parcel is recorded as farmland → in reality there's a functioning hotel on it.
A residential plot is registered → but the house built on it was never added to ДРРП.
A building was legally terminated years ago → but still counts as active for taxation.

This leads to:

- **Lost budget revenue** — unpaid and under-paid property tax.
- **Inefficient resource management** — communities do not know what they actually own.
- **Lack of transparency** — citizens and deputies have no source of truth.

Today, reconciliation is done **manually in Excel** by a single землевпорядник per community, with no bridge to inspectors in the field. Discrepancies are found by luck, not by system.

---

## 2. The Solution — E-State

E-State is a platform that **automates the search for discrepancies** between ДЗК and ДРРП, and turns them into a **prioritised action plan** for inspectors and municipal leadership.

Input: the same two Excel files the землевпорядник already has.
Output in **under 10 seconds**:

1. A ranked list of critical, warning, and informational findings.
2. A mobile-first workflow for the inspector — "I know exactly where to go and why."
3. A canonical `verified_asset` table: one row per reconciled property, updated by field visits.
4. A transparent citizen portal: check your own records by РНОКПП.
5. Budget-impact projections + a one-click executive report for deputies.

### Secret sauce

> We don't just highlight mismatches — we build the **bridge between the землевпорядник's desk and the inspector's feet.** The inspector finally knows exactly where to go, why, and what to verify.

---

## 3. Users & Stakeholders

| Persona | Role | Device | What they get |
|---|---|---|---|
| **Землевпорядник** | Back-office analyst | Desktop | Dashboard, upload, findings table, analyst → inspector assignment |
| **Інспектор** | Field auditor | Mobile-first | Prioritised queue, compare view ДЗК vs ДРРП, visit form, source-of-truth selector |
| **Мешканець** | Citizen | Mobile/desktop | Public РНОКПП lookup — "Are my records synchronised?" |
| **Голова ОТГ / Депутат** | Read-only leadership | Desktop | Reports, budget-impact, executive PDF |

---

## 4. MVP Features — What's Built & How It Works

The MVP is a full three-role flow end-to-end on the **real provided dataset** (21 656 land parcels × 20 382 real-estate rows; 10 937 shared taxpayers).

### 4.1 Data ingestion (`/upload`)

**What it does:** accept two registry files (ДЗК + ДРРП) in `.xlsx` or `.csv`, persist them as a new `dataset_id`.

**How it works:**

- Two drop zones, one per registry, with client-side validation (file type, size < 25 MB).
- Backend reads with Pandas, runs a **normalization layer** (`services/api/app/ingest/`):
  - Column name unification across registry variants.
  - `га → м²` area conversion.
  - Excel-serial → ISO dates.
  - Latin/Cyrillic homoglyph fix on object types (`і` vs `i`).
  - КОАТУУ code cleanup and taxpayer-ID normalisation.
- Raw rows stored with a stable `dataset_id`. Source XLSX lifecycle-deleted after 90 days (compliance).

### 4.2 Cross-registry matcher (`/matcher/run`)

**What it does:** produce the complete set of `finding` rows — ranked discrepancies between the two registries.

**How it works:**

- **Join key is taxpayer ID** (`РНОКПП` / `ЄДРПОУ`). This was a key correction from the original PRD — the supplied ДРРП has **no cadastral numbers**, so we join on taxpayer instead of address, giving a **deterministic 100% match** on 10 937 shared persons.
- Fallback: fuzzy normalized-name match within the same КОАТУУ (`rapidfuzz.token_set_ratio ≥ 0.92`).
- **8 detectors run in parallel**, each a pure `DataFrame → list[Finding]` function:

| # | Detector | Trigger | Severity |
|---|---|---|---|
| 1 | `AREA_PORTFOLIO_DELTA` | `re_m² / land_m² > 1.25` | **Critical** |
| 2 | `LAND_NO_REAL_ESTATE` | Residential land (`02.01`), no residential ДРРП | Warning |
| 3 | `REAL_ESTATE_NO_LAND` | Active real estate, no land at all | Warning |
| 4 | `USE_VS_OBJECT_MISMATCH` | Agri land + commercial building | **Critical** |
| 5 | `OWNER_NAME_MISMATCH` | Same tax ID, `token_set_ratio < 0.85` | Warning |
| 6 | `TERMINATED_BUT_ACTIVE` | Terminated in ДРРП, still counted | Info |
| 7 | `MISSING_OWNER` | ДЗК row with blank taxpayer | **Critical** |
| 8 | `DUPLICATE_REGISTRATION` | Same cadastral, conflicting owners | **Critical** |

- Every finding is **explainable**: carries `computed_metrics` (the numbers that justified it) and `evidence_refs` (ids of the exact ДЗК/ДРРП rows used).
- **Deterministic and idempotent** — rerun on the same data gives identical findings. Enforced by `UNIQUE(dataset_id, person_tax_id, finding_type)`.
- **Performance target:** full pipeline on 21 656 × 20 382 rows in **< 10 s** on a laptop.

### 4.3 Back-office dashboard (`/dashboard`)

**What it does:** bird's-eye view of the community's asset state.

**How it works:**

- 3 KPI tiles: **Total records**, **Mismatches found** (detection-rate %), **Files processed**.
- Recent discrepancies card — top 3 findings with severity dot, deep-link to the full list.
- Two hero tiles: "Detection rate" (big % on forest-green) + "Last analysis" (warm-sand CTA).

### 4.4 Findings workbench (`/findings`)

**What it does:** dense, scannable, filterable table of every finding.

**How it works:**

- Summary strip: `Критичні`, `Попередження`, `Інформаційні` counts.
- Filters: severity chips, `finding_type` multiselect, КОАТУУ, debounced person search.
- Columns: masked person, type, severity badge, locality, detected at, status, actions.
- Row actions: **Призначити інспектору**, **Відхилити**.
- Users identify "Critical" issues within 3 seconds (design invariant).

### 4.5 Finding detail — deep dive (`/findings/:id`)

**What it does:** the "workhorse" screen where the analyst decides whether to dispatch an inspector.

**How it works:**

- **Plain-language explanation** of the metric:
  > "Сумарна площа нерухомості (6 989.7 м²) у 7.74 раз перевищує площу земельних ділянок (903 м²). Імовірна причина: незареєстрована або неправильно класифікована ділянка."
- **Split-screen**: left card ДЗК (all land parcels for this person), right card ДРРП (all real-estate rows). Divergent fields auto-highlighted in rose tone.
- **Assign-to-inspector** card: free-text note + `Передати на перевірку` button → `POST /findings/{id}/assign`. Status flips `open → in_review`. Note surfaces directly on the inspector's mobile card.
- **Visits timeline**: chronological list of all `FieldVisit` entries on this finding.

### 4.6 Inspector mobile flow (`/inspector`)

**What it does:** turn a "red" finding into a verified truth record.

**How it works:**

- Mobile-first list of assigned findings, sorted by severity → КОАТУУ → distance (if GPS allowed).
- Detail screen:
  1. **Summary card** — type, severity, masked РНОКПП, top computed metrics.
  2. **Assignment-note banner** — the analyst's guidance, on-site.
  3. **Compare view** — two columns (ДЗК / ДРРП), divergent fields highlighted. Each column has an `Обрати як істину` button.
  4. **Truth-source selector** — `Дані ДЗК` / `Дані ДРРП` / `Дані з огляду`. Picking ДЗК or ДРРП auto-fills the form from that snapshot; picking `Огляд` keeps the form editable so the inspector can record reality when neither registry is correct.
  5. **Visit form** — actual type / area / use / notes + GPS capture + photo upload.
  6. **Resolution toggle** — `Розв'язано` or `Потребує додаткової перевірки`.
- Submit → `POST /inspector/visits`. When `resolution === "resolved"`, the server **upserts a `verified_asset` row** — the canonical "main table."

### 4.7 Verified asset registry (the main table)

**What it does:** the canonical, immutable-by-design record of what is actually on each parcel, reconciled by a field visit.

**How it works:**

- **ДЗК and ДРРП snapshots are never mutated** — we keep them for audit.
- Every downstream read (analyst detail, citizen portal, reports) reads `verified_asset`, not the raw registries.
- One row per `finding_id`. Includes `source_of_truth` (`dzk` | `drrp` | `inspection`) + `truth_evidence_id`.
- Re-submitting a visit overwrites the row.

### 4.8 Citizen portal (`/citizen`)

**What it does:** public, unauthenticated self-check.

**How it works:**

- Public landing page explains the legal basis and the ОТГ's right to audit (link to `/legal`).
- `/citizen/lookup`: single form — РНОКПП + CAPTCHA.
- Results page shows only: masked tax ID, full name, record counts, one of three status badges:
  - `Дані синхронізовано` (green) — no open findings.
  - `Потребує уточнення` (warning) — ≥ 1 open finding, citizen-safe summary, never citing neighbours.
  - `Триває перевірка` (info) — assigned to an inspector.
- Link `Як оновити дані` — concrete templates for ЦНАП or online filing.

### 4.9 Reports & budget impact (`/reports`)

**What it does:** quantify the economic effect for leadership.

**How it works:**

- KPI strip: `Очікуване зростання податкових надходжень`, `Резолюції інспекторів`, `% red → green`.
- Budget-impact chart (Recharts) from `GET /reports/budget-impact`.
- Executive summary card (top localities, status mix, caveats).
- Exports:
  - **CSV** — current filters applied.
  - **XLSX** — current filters + summary tab.
  - **PDF** — deputy-ready executive briefing.
- PII default is `masked`; `full` exports are admin-only and audit-logged.

### 4.10 Cross-cutting features

- **Audit log.** Every write (matcher run, finding assignment, visit, citizen lookup) writes a row to `audit_log` with correlation ID.
- **РНОКПП masking.** Never in URLs, query strings, or client logs. Displayed as `***NNNN` everywhere except the one authenticated detail endpoint.
- **Status machine.** `open → in_review → resolved | dismissed`, with admin reopen within 14 days.
- **Empty / loading / error states.** Every list-backed screen has explicit skeletons and empty-state illustrations — never blank space.
- **Accessibility.** All interactive elements keyboard-reachable; status is never colour-only (every badge has text + icon); minimum 16 px body text.
- **i18n ready.** All user-facing strings in `apps/web/src/i18n/uk.ts`; code and identifiers in English.

---

## 5. Architecture at a Glance

```
apps/web/            Next.js 15 App Router (back-office, inspector, citizen)
services/api/        FastAPI + Pandas (ingest, matcher, api, security, reports)
docs/                Authoritative specs (architecture, matcher, API, flows)
```

- **Backend:** FastAPI (Python 3.12) + Pandas + `rapidfuzz` + SQLAlchemy + SQLite (dev) / Postgres (prod).
- **Frontend:** Next.js 15 + Tailwind + Shadcn/ui + Lucide icons. SSR for citizen-portal SEO.
- **Invariant:** business logic lives in `matcher` and `domain` — never in API routers, never in React components.
- **Deployment:** `apps/web` on Vercel, API on Fly.io / Render, object storage on Cloudflare R2 or Supabase Storage.

---

## 6. Proof on the Real Dataset

Worked examples from the provided `ДРРП земля.xlsx` / `ДРРП нерухомість.xlsx`:

| Case | Person (masked) | Finding | Signal |
|---|---|---|---|
| Clean baseline | `***7363` Тодирюк Василь | — | Control row, no detector fires |
| `AREA_PORTFOLIO_DELTA` critical | `***3371` Хоцевич Григорій | ratio 7.74× | Land 903 m² vs active RE 6 989.7 m² |
| `AREA_PORTFOLIO_DELTA` warning | `***1657` Турко Богдан | ratio 2.73× | Probable unregistered structure |
| `LAND_NO_REAL_ESTATE` | `***5242` Пастернак Віталій | 1 residential parcel, no house in ДРРП | Classic "house built, never filed" |
| `LAND_NO_REAL_ESTATE` extreme | `***9364` Ковальчук Мирослав | residential land, zero ДРРП rows | Highest-signal case on dataset |
| `TERMINATED_BUT_ACTIVE` | `***5171` Музичук Надія | terminated 2015, still counted | 5 080 such rows total |

**Dataset-level baselines (locked in `tests/baselines.json`):**

- 21 656 land rows × 20 382 real-estate rows.
- 10 937 persons present in both registries.
- 470 persons only in ДЗК, 0 only in ДРРП.
- 5 080 terminated-but-active real-estate rows.
- 0 duplicate cadastrals, 0 missing owners (clean data — detectors still ship for production).

---

## 7. Legal Basis

- Law of Ukraine **"Про місцеве самоврядування"** art. 26, 33.
- **Земельний кодекс України** art. 12, 83 — ОТГ authority over communal land.
- **We do not write to official registries.** We produce analytical recommendations; legal decisions stay with the posadova osoba.
- **PII compliance:** РНОКПП masked by default, full ID only on authenticated detail endpoints, every access audit-logged.
- Pre-pilot: legal sign-off by ОТГ's lawyer; on-prem / dedicated-VPC deployment available for data-sensitive communities.

---

## 8. Business Model

**Primary: SaaS subscription per ОТГ**, tiered on population.

| Tier | ОТГ population | Monthly (UAH) | Included |
|---|---|---|---|
| Starter | < 5 000 | 4 900 | 1 admin, 2 inspectors, ≤ 4 datasets/mo |
| Standard | 5 000 – 20 000 | 12 900 | 3 admins, 6 inspectors, unlimited datasets |
| Pro | 20 000 – 100 000 | 29 900 | + Satellite monitoring, API access |
| Enterprise | > 100 000 / multi-ОТГ | Custom | + SSO, SLA 99.9 %, on-prem |

**Secondary streams:**

- **Inspector pack** — +490 UAH/month per additional inspector seat.
- **Success fee option** — 4–6 % of first-year tax uplift attributable to resolved findings. Tracked via `field_visit` → finding resolution linkage. Opt-in.
- **Consulting & customisation** — bespoke detectors, legacy imports, training.

**Unit economics:**

- Gross margin **> 75 %** at Standard tier.
- Payback **< 3 months** per signed ОТГ.
- Onboarding cost target: **1–2 days per ОТГ** — zero on-prem install, zero IT-team dependency.

---

## 9. Scaling Strategy

- **Horizontal:** one SaaS cluster serves many ОТГ via tenant isolation (per-tenant Postgres schema + object-storage prefix).
- **Content packs:** `matcher/config.py` profiles per region (farmland ratios, urban vs rural thresholds) ship as named presets.
- **Localisation:** UI in Ukrainian; copy tables allow per-область overrides.
- **Pilot formula:** **1 ОТГ = 2 Excel files = pilot running in 48 hours.**

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ОТГ hesitant to share data | On-prem / VPC deployment; source XLSX lifecycle-deleted in 90 days; open audit log |
| Data-quality inconsistencies (Latin/Cyrillic mixups, messy КОАТУУ) | Documented normalization layer; tests against real samples; tuneable thresholds |
| Legal ambiguity around auto-matching РНОКПП | ОТГ lawyer sign-off pre-pilot; **no registry writes**; RNOKPP masking by default |
| Inspector change management | Mobile flow optimised for ~5 min/visit; clear severity prioritisation; training materials |
| False accusation of a citizen | "Presumption of regularity" UI language; reopening window; no public shaming |
| Competition from bespoke 1С modules | Faster onboarding (days vs months), modern UX, open API, transparent pricing |
| Registry-API changes | Adapter pattern in `ingest/`; one module per source format |

---

## 11. Roadmap

| Horizon | Features |
|---|---|
| **MVP (Hackathon)** | 3-role flow end-to-end, 8 detectors live on real data, single-tenant SQLite |
| **v1 — Pilot (1 ОТГ)** | Multi-tenant Postgres, satellite monitoring (Sentinel-2 change detection), SSO (ID.gov.ua / BankID), ГІС export |
| **v2 — 5–10 ОТГ** | Дія push notifications, public transparency portal, API for external auditors, native Android |
| **v3 — Regional scale** | Cross-ОТГ analytics for обласна державна адміністрація, AI photo classification, revenue-share module |

---

## 12. Success Metrics (pilot targets @ 12 months)

- **≥ 8 %** tax-revenue uplift in pilot ОТГ.
- **≥ 12 %** of detected findings resolved within 30 days.
- **≥ 90 %** inspector satisfaction on the mobile flow.
- Monotonic improvement of the data-quality score (share of ДРРП records with a valid, active `owner_tax_id` and no termination flag).

---

## 13. Long-Term Vision

E-State evolves in three arcs:

1. **From audit to lifecycle.** Today we find stale records. Next we *manage* the lifecycle: alerts on new registrations, auto cross-checks on satellite change, citizen self-update prompts.
2. **From one ОТГ to the system.** Aggregate, anonymised signals become a tool for обласна державна адміністрація and ministerial oversight — the strategic moat.
3. **From compliance to revenue.** Once data is trustworthy, E-State surfaces *opportunities* — unused communal parcels suitable for leasing, underused buildings — not only discrepancies.

---

## 14. Team & Demo

- **Speaker 1 — Product/CEO:** problem, solution, legal, business model, scaling, metrics.
- **Speaker 2 — AI/Data Engineer:** live MVP demo, technical architecture.
- **Speaker 3 — Ops/Inspector lead:** inspector mobile flow, field experience, Q&A.

**9-minute format:** 5 min business · 2 min live demo · 2 min Q&A. Full script in [demo-script.md](demo-script.md).

---

> **"Ми сфокусувалися на операційній ефективності. Звіт для депутатів генерується однією кнопкою, але головна цінність — це робота інспектора, який нарешті знає, куди саме йому йти, а не шукає порушення навпомацки."**
