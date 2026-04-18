# E-State — Правові межі та відповідність

> Map of the legal basis E-State operates under, the rights of third parties, and the concrete product rules that enforce them. Cited from the "Правові межі та відповідність" criteria in [task.md](task.md) and the "Правова база" slide in [PRD.md](PRD.md).

> Disclaimer: this is the product team's working interpretation. Before production deployment, the ОТГ's юрист has to sign off on the specific postanovy and localized act references.

## 1. Legal basis for E-State's operation

E-State surfaces discrepancies between two public-sector registries for an ОТГ that already has the legal right to manage communal property. Our reading:

| Basis | What it authorises |
|---|---|
| Конституція України, ст. 140–144 | Право територіальних громад самостійно управляти комунальним майном |
| Закон України "Про місцеве самоврядування в Україні", ст. 26, 33 | Повноваження ОТГ щодо контролю за використанням земель та комунального майна |
| Земельний кодекс України, ст. 12, 83 | Розпорядження землями комунальної власності належить ОТГ |
| Закон України "Про Державний земельний кадастр" | Легальний доступ уповноважених посадових осіб до даних ДЗК |
| Закон України "Про державну реєстрацію речових прав на нерухоме майно…" | Регламентує роботу ДРРП та доступ до відомостей |
| Постанови КМУ про цифровізацію публічних послуг | Підстава для електронного зведення реєстрів в інтересах ОТГ |

E-State's role is **analytical**: it highlights potential discrepancies for a posadova osoba to investigate. It does **not** issue rulings, fines, or amend the registries directly.

## 2. Boundaries of authority (must-not-do list)

- **Do not** alter the source registries. Writes happen only to E-State's own DB (`finding`, `field_visit`, `audit_log`).
- **Do not** publish owner-level data on a public page. The citizen portal shows **only the person's own** records, gated by CAPTCHA and rate limits.
- **Do not** auto-assess taxes. `/reports/budget-impact` produces an *estimate* labelled as such, with caveats rendered in the UI.
- **Do not** enable a posadova osoba of ОТГ "A" to query residents of ОТГ "B". Multi-tenant isolation by `ОТГ tenant_id` is a v1 deliverable (see [roadmap.md](roadmap.md)).

## 3. Захист персональних даних

Anchored in Закон України "Про захист персональних даних" (ст. 5, 8, 11, 24) and GDPR-compatible hygiene.

### 3.1 Classification

| Category | Examples | Treatment |
|---|---|---|
| Personal data (PD) | РНОКПП, ПІБ, адреса об'єкта, дата народження (похідно) | Minimised, masked in logs, access-logged |
| Public-registry data | Кадастровий номер, цільове призначення, площа ділянки | Not PD on its own; becomes PD when linked to a specific person |
| Sensitive | None handled by E-State MVP | — |

### 3.2 РНОКПП handling rules (code-enforced)

Enforced by the `e-state-pii` Cursor rule:

- **Never** in URLs or query strings. Always in request bodies.
- **Never** in client logs, console output, or error messages.
- **Masked everywhere** in server logs: `***NNNN` (last 4 digits only).
- **Never** returned in list endpoints. List views return `tax_id_masked`; full `tax_id` only on detail endpoints, and always after writing an `audit_log` row (`action = read_citizen`).
- **Not used as a DB primary key at the UI layer.** Internally the `person.tax_id` PK is fine, but the web client uses finding UUIDs for routing.

### 3.3 Citizen consent and transparency

- Citizen portal carries a privacy notice at `/legal/privacy` — plain-language, Ukrainian, one page — explaining:
  - What data E-State shows you.
  - What data we store about the lookup.
  - How to request correction or deletion.
- Lookups are logged as `audit_log` with `actor = citizen:***NNNN` so citizens can request their own access history.

## 4. Захист інтересів третіх осіб

Per task criterion 1.3.2, E-State must protect third-party interests when a discrepancy is flagged:

- **Presumption of regularity.** UI language never calls a record "illegal". It says "потребує уточнення", "розбіжність", "очікує перевірки". The `USE_VS_OBJECT_MISMATCH` finding is a *hypothesis*, not a finding of fact.
- **Right to be heard.** The Inspector's field-visit form requires structured evidence (photos + GPS + notes). Resolutions that contradict the owner must carry supporting photos.
- **Reopening window.** `resolved` / `dismissed` findings can be reopened for 14 days (see [user-flows.md §6](user-flows.md#6-state-transitions)). After that, any reinvestigation creates a new dataset.
- **No public shaming.** The citizen portal tells a person *their own* status. There is no public "shame list".

## 5. Audit obligations

Anchored in general good practice and the requirement that ОТГ decisions be defensible.

Every write to `finding`, `field_visit`, or lookup of a citizen's data produces one `audit_log` row (see [data-model.md §2.9](data-model.md#29-audit_log)). The log:

- Is append-only (no UPDATE, no DELETE — enforced by Postgres trigger in prod).
- Stores a SHA-256 payload hash, **never the payload itself**.
- Is retained for **5 years** — matches the standard retention for ОТГ decision documents.

## 6. Data retention

| Data | Retention | Notes |
|---|---|---|
| Source xlsx uploads | 90 days | Object-storage lifecycle rule |
| Normalized `land_parcel` / `real_estate` rows | Retained per dataset; anonymised after 2 years by blanking `owner_tax_id` and `owner_name_raw` | |
| `finding` | 5 years | For audit |
| `field_visit` photos | 5 years, then compressed and archived | |
| `audit_log` | 5 years, append-only | |
| Citizen lookup records | 90 days, then aggregated only | |

Deletion workflows live behind a staff-admin-only `/admin/retention` page (post-MVP).

## 7. Security baseline

- TLS 1.2+ everywhere. HSTS on the web host.
- JWTs signed with rotating asymmetric keys; session lifetime 8 h for staff, 12 h for inspectors.
- Rate limiting: 5 / 15 min / IP on citizen lookup; 60 / min on authenticated endpoints.
- CAPTCHA on citizen portal.
- Secrets in env vars only; no secrets in git. [.env.example](../services/api/.env.example) is the canonical list.
- Dependency scanning in CI (`pip-audit` + `npm audit`).

## 8. What a "правова довідка" slide in the demo should say

Lifted from the PRD's "Правова база" slide:

> E-State діє як аналітичний інструмент у межах повноважень ОТГ щодо комунального майна. Система не вносить змін у ДЗК/ДРРП, не публікує персональних даних мешканців і ніколи не виносить юридичних рішень. Всі розбіжності мають статус гіпотез до підтвердження інспектором, а власник має право бути вислуханим.

## 9. Known open questions (pre-production)

1. Exact ОТГ резолюція or договір that authorises E-State to ingest the ДЗК extract — to be supplied by the ОТГ's юрист before pilot.
2. Whether the budget-impact endpoint can be shown outside the ОТГ internal perimeter (депутатам yes; публічно — no).
3. Multi-tenant isolation plan in the hosted SaaS version — tracked in [roadmap.md](roadmap.md).
