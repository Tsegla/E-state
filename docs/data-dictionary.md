# E-State — Data Dictionary

> Cross-walk from the real input files in this repo to canonical English snake_case fields used everywhere downstream. All normalization rules are authoritative; the `ingest/` module must follow them exactly.

## 1. Source files (verified)

- **ДЗК (земля):** [docs/ДРРП земля.xlsx](ДРРП%20земля.xlsx) — 21 656 rows × 16 columns, sheet `Sheet`.
- **ДРРП (нерухомість):** [docs/ДРРП нерухомість.xlsx](ДРРП%20нерухомість.xlsx) — 20 382 rows × 9 columns, sheet `Аркуш1`.

Dataset facts established from the real files:

- `10 937` persons appear in both registries (matching via taxpayer ID).
- `470` persons appear only in ДЗК (own land, no real-estate record).
- `0` persons appear only in ДРРП.
- `5 080` ДРРП rows have a non-empty termination date (`Дата держ. реєстр. прип. права власн`).
- `0` duplicate cadastral numbers in ДЗК on this dataset.
- `0` ДЗК rows with an empty taxpayer ID.

These baselines matter because they tell us which detectors will fire in the demo (e.g. `DUPLICATE_REGISTRATION` returns empty on this specific dataset — see [data-matcher-spec.md](data-matcher-spec.md)).

## 2. ДЗК cross-walk

| Source header (UA) | Canonical field | Type | Normalization |
|---|---|---|---|
| `Кадастровий номер` | `cadastral_no` | `str` | Uppercase, strip whitespace, validate `^\d{10}:\d{2}:\d{3}:\d{4}$` |
| `koatuu` | `koatuu` | `str` | Left-pad to 10 digits |
| `Форма власності` | `ownership_form` | enum | `приватна|державна|комунальна|колективна|інша` (lowercased) |
| `Цільове призначення` | `intended_use_code`, `intended_use_label` | `(str, str)` | Split on first space: `"02.01 Для будівництва..."` → `code="02.01"`, `label="Для будівництва..."`. If no numeric prefix, `code=None`, `label=raw`. |
| `Місцерозташування` | `location_admin` | `str` | Trim, collapse internal whitespace. Do **not** confuse with street address. |
| `Вид с/г угідь` | `agri_use_kind` | `str` | Trim, title-case for display |
| `Площа, га` | `area_m2` | `float` | Parse as float, multiply by `10_000` (га → m²). Store m². |
| `Усереднена нормативно грошова оцінка` | `valuation_uah` | `float` | Parse as float |
| `ЄДРПОУ землекористувача` | `owner_tax_id` | `str` | Strip whitespace, keep leading zeros. Valid if digits only, length ∈ `{8,10}`. |
| `Землекористувач` | `owner_name_raw` | `str` | Keep raw; `owner_name_norm` = lowercase + strip + replace `ё→е`. |
| `Частка володіння` | `share` | `float` | Parse; fallback `1.0` if blank |
| `Дата державної реєстрації права власності` | `registered_at` | `date` | Excel serial → ISO date (see §4) |
| `Номер запису про право власності` | `record_no` | `str` | Keep as-is |
| `Орган, що здійснив державну реєстрацію права власності` | `registrar` | `str` | Trim |
| `Тип` | `record_kind` | `str` | e.g. `відомості з ДЗК`, `інший` |
| `Підтип` | `record_subkind` | `str` | Trim |

## 3. ДРРП cross-walk

| Source header (UA) | Canonical field | Type | Normalization |
|---|---|---|---|
| `Податковий номер ПП` | `owner_tax_id` | `str` | Same rule as ДЗК |
| `Назва платника` | `owner_name_raw` | `str` | Same rule as ДЗК |
| `Тип об'єкта` | `object_type_raw`, `object_type_norm` | `(str, str)` | See §5 — normalizes `квартира/квартира`, `будiвля→будівля` (Latin `i` → Cyrillic `і`) |
| `Адреса об'єкта` | `address_raw`, `address_norm` | `(str, str)` | `address_norm` = lowercase, strip diacritics for fuzzy; street address, not administrative |
| `Дата держ. реєстр. права власн` | `registered_at` | `date\|null` | Excel serial → ISO date |
| `Дата держ. реєстр. прип. права власн` | `terminated_at` | `date\|null` | Excel serial → ISO date. **Non-null means the right is terminated.** |
| `Загальна площа` | `area_m2` | `float` | Already in m², parse as float |
| `Вид спільної власності` | `joint_ownership_kind` | enum\|null | `спільна часткова|спільна сумісна|null` |
| `Розмір частки у праві спільної власності` | `share` | `float` | Parse; if equal to `area_m2` then normalize to `1.0` (common data-entry pattern in the provided file) |

## 4. Excel serial → ISO date

Excel serial dates use the `1900-01-01` epoch with the infamous leap-year bug, so in Python the safe conversion is:

```python
from datetime import date, timedelta

def excel_serial_to_iso(value: str | float | None) -> str | None:
    if value in (None, "", 0):
        return None
    days = int(float(value))
    return (date(1899, 12, 30) + timedelta(days=days)).isoformat()
```

Sanity checks from the real file:

| Serial | ISO |
|---|---|
| `45055` | `2023-05-09` |
| `42101` | `2015-04-07` |
| `41309` | `2013-02-04` |

## 5. `object_type_norm` mapping

The ДРРП file mixes Latin `i` and Cyrillic `і` inside the same word (e.g. `будiвля` vs `будівля`, `гаражi`, `нежиле примiщення`). The normalizer collapses both to a canonical lowercased Cyrillic form and groups synonyms:

| Canonical | Merges |
|---|---|
| `квартира` | `квартира` |
| `житловий_будинок` | `житловий будинок`, `будинок`, `садовий будинок` |
| `гараж` | `гаражi`, `гараж` |
| `нежитлова_будівля` | `нежитлова будiвля`, `нежитлова будівля`, `будiвля`, `будівля` |
| `нежитлове_приміщення` | `нежиле примiщення`, `нежитлове примiщення`, `примiщення`, `нежитлове приміщення` |
| `промислова_будівля` | `будiвлi промисловостi та склади`, `iншi будiвлi` |
| `торгова_будівля` | `будiвлi торговельнi` |
| `офісна_будівля` | `будiвлi офiснi` |
| `інше` | `iнше`, everything else |

Top-15 distributions observed in the raw data (for matcher baselines):

```
12854  квартира
 4094  житловий будинок
 1921  будинок
  515  гаражi
  241  нежитлова будiвля
  205  нежиле примiщення
  182  iнше
  160  нежитлове примiщення
   62  будiвля
   60  садовий будинок
   33  будiвлi промисловостi та склади
   16  будiвлi торговельнi
   14  iншi будiвлi
   11  примiщення
    3  будiвлi офiснi
```

## 6. `intended_use_code` — authoritative list (ДЗК observed)

Top codes appearing in this dataset (with implied residential/agricultural semantics used by detectors):

| Code | Label prefix | Detector class |
|---|---|---|
| `01.01` | товарного сільськогосподарського виробництва | agricultural |
| `01.03` | особистого селянського господарства | agricultural |
| `01.04` | підсобного сільського господарства | agricultural |
| `01.05` | індивідуального садівництва | agricultural |
| `01.06` | колективного садівництва | agricultural |
| `02.01` | житлового будинку, господарських будівель | residential |
| `02.03` | блокованого житлового будинку | residential |
| `02.05` | індивідуальних гаражів | auxiliary |
| `02.06` | колективного гаражного будівництва | auxiliary |
| `03.07` | будівель торгівлі | commercial |
| `11.02`, `11.04` | промислового призначення | industrial |
| `14.02` | транспорту | infrastructure |
| `16.00` | (запас/резерв) | reserved |

Rows where the code cannot be parsed (raw label starts with `Для …` without a numeric prefix) fall into `intended_use_code = None` and are **excluded from class-based detectors** but still counted in record totals.

## 7. Owner-name normalization

Used as the fallback join key and for `OWNER_NAME_MISMATCH`:

```python
def normalize_name(raw: str) -> str:
    s = raw.strip().lower().replace("ё", "е")
    s = " ".join(s.split())
    return s
```

Fuzzy compare with `rapidfuzz.fuzz.token_set_ratio(a, b) / 100.0`.

## 8. Primary vs fallback join keys

1. **Primary:** `owner_tax_id` equality (`ЄДРПОУ землекористувача` ↔ `Податковий номер ПП`).
2. **Fallback:** `normalize_name(zem_name) == normalize_name(ner_name)` **and** `token_set_ratio ≥ 0.92` **and** same `koatuu` / administrative prefix — only when either side has a missing or malformed tax ID. On the provided dataset this fallback never fires, but the matcher must implement it for production data quality.

## 9. Units and conventions

- Areas are stored in **m²** everywhere in the canonical model, regardless of input unit.
- Money is stored in **UAH**, integer kopecks (`valuation_kop = round(uah * 100)`). API serializes as decimal strings.
- Dates are ISO strings in JSON (`YYYY-MM-DD`).
- Taxpayer IDs are strings (never integers — they may have leading zeros).
