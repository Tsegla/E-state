# E-State — Sample Findings (Worked Examples)

> Concrete walk-throughs on real rows from the provided [docs/ДРРП земля.xlsx](ДРРП%20земля.xlsx) and [docs/ДРРП нерухомість.xlsx](ДРРП%20нерухомість.xlsx). Use these as (a) shared reference when discussing detectors, (b) basis for golden-set fixtures, and (c) stage-ready stories for the demo.

All tax IDs below are shown **masked** in the style the UI must use. Non-masked forms appear only inline for traceability during development; in any UI screenshot they must be `***NNNN`.

## 1. Baseline (clean): Тодирюк Василь Тодорович

- Tax ID: `***7363` (full: `2247237363`).
- ДЗК: кадастр `4611800000:03:008:0100`, Приватна, `02.01 Для будівництва і обслуговування житлового будинку…`, Львівська область м. Червоноград, вул. Т.Савки 17, `545 м²` (0.0545 га), зареєстровано `2017-11-17`.
- ДРРП: квартира, `вулиця Шевченка, будинок 12, квартира 30`, `45 м²`, зареєстровано `2004-09-18`, терміновано — ні.

**Expected detectors:** none. This person ships as the clean-baseline control fixture (`tests/fixtures/sample_baseline.csv`).

## 2. `AREA_PORTFOLIO_DELTA` — critical

Хоцевич Григорій Степанович, tax ID `***3371` (`2757803371`).

| Side | Records | Summed area (m²) |
|---|---|---|
| ДЗК | 2 parcels | 903 |
| ДРРП (active) | 2 objects | 6 989.7 |

`ratio = 6989.7 / 903 = 7.74` → exceeds the `critical` threshold of `1.25`.

**Plain-language explanation in UI:**

> Сумарна площа нерухомості (6 989.7 м²) у 7.74 раз перевищує площу земельних ділянок цієї особи (903 м²). Імовірна причина: незареєстрована або неправильно класифікована ділянка.

**Computed metrics shape:**

```json
{
  "land_m2": 903.0,
  "re_m2_active": 6989.7,
  "ratio": 7.74,
  "terminated_count": 0
}
```

Other confirmed rows on the real dataset that fire this detector: `***1657` (Турко Богдан Ігорович, ratio ≈ 2.73), `***5714` (Сокальська Людмила Єфімівна, ratio ≈ 2.39).

## 3. `LAND_NO_REAL_ESTATE` — warning (residential land, no residential building)

Three confirmed real-dataset candidates:

| Person | Tax ID | ДЗК land | ДРРП objects |
|---|---|---|---|
| Пастернак Віталій Олександрович | `***5242` | `02.01` житловий | `iнше` only |
| Бєлінський Федір Миколайович | `***7669` | `02.01` житловий | `нежиле примiщення` only |
| Малетич Тетяна Василівна | `***4477` | `02.01` житловий | `гаражi` only |

Detector fires because there's **no** entry with `object_type_norm ∈ {квартира, житловий_будинок}` for these persons — yet they own residential-intent land. Classic pattern: дім побудовано, у ДРРП не внесено.

**Computed metrics shape:**

```json
{
  "residential_parcels": 1,
  "total_residential_m2": 1250.0
}
```

## 4. `LAND_NO_REAL_ESTATE` — warning (extreme: no ДРРП record at all)

Three confirmed candidates with residential-intent land but **zero** ДРРП rows:

| Person | Tax ID |
|---|---|
| Ковальчук Мирослав Петрович | `***9364` |
| Петрина Ярослава Микитівна | `***6612` |
| Возний Михайло Стахович | `***8575` |

These are the highest-signal cases on the dataset — resident owns a building-intent parcel and is entirely absent from ДРРП. Worth a inspector field-visit in the demo.

## 5. `TERMINATED_BUT_ACTIVE` — info

5 080 ДРРП rows on this dataset carry a termination date. Three verified examples:

| Person | Tax ID | Object | `terminated_at` |
|---|---|---|---|
| Музичук Надія Олексіївна | `***5171` | квартира | `2015-04-07` |
| Домашевич Богдан Дмитрович | `***6083` | квартира | `2015-04-07` |
| Смоляр Галина Миколаївна | `***1837` | житловий будинок | `2018-07-12` |

Because this is info-only by itself, don't flood the dashboard. The UI tier promotes these to `warning` when combined with any other open finding on the same person.

## 6. `OWNER_NAME_MISMATCH` — warning (no hits on this dataset)

On the supplied data the normalizer produces identical names across registries for every shared tax ID, so this detector emits zero findings. The fixture for testing the detector must therefore be synthetic — construct a tiny CSV with:

```
tax_id, land_owner_name, realestate_owner_name
***5171, Музичук Надія Олексіївна, Музичук Н. О.
```

(`token_set_ratio ≈ 0.71 < 0.85` threshold.)

## 7. `MISSING_OWNER` and `DUPLICATE_REGISTRATION` — not present in real data

Both return zero on the supplied dataset. Detectors still ship; their fixtures are synthetic:

- `MISSING_OWNER`: a ДЗК row with blank `ЄДРПОУ землекористувача`.
- `DUPLICATE_REGISTRATION`: two ДЗК rows sharing `Кадастровий номер` but with different `ЄДРПОУ землекористувача`.

## 8. Source snapshot (for reference)

The dataset-level facts observed during planning, locked in `services/api/tests/baselines.json`:

```json
{
  "zem_rows": 21656,
  "ner_rows": 20382,
  "persons_in_both": 10937,
  "persons_only_zem": 470,
  "persons_only_ner": 0,
  "ner_terminated_rows": 5080,
  "zem_duplicate_cadastral": 0,
  "zem_missing_owner": 0
}
```

The pipeline test re-asserts each of these after a full ingest+matcher run to catch regressions in the normalization layer.
