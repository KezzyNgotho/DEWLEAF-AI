# External Datasets & Provenance

## Included (downloaded/generated)

| Dataset | Path | Rows | Notes | License/Source |
|---|---:|---:|---|---|
| Open-Meteo ERA5 archive, 47 KE counties, 2024 | `ml/data/open_meteo/2024/*.csv` | ~412,000 hourly | Free API, no key | Open-Meteo/CC-BY 4.0 |
| Open-Meteo ERA5 archive, 47 KE counties, 2023 | `ml/data/open_meteo/2023/*.csv` | ~411,000 hourly | Free API, no key | Open-Meteo/CC-BY 4.0 |
| DewLeaf physics-informed training rows | `ml/data/dewleaf_kenya_weather_2023_2024.csv` | 446,641 | Derived night-window rows, **synthetic labels** | Generated in-repo |

## Investigated but not ingested

| Source | Reason |
|---|---|
| Zenodo 20712128 TEC-AWG dataset | API/file access returned 404/restricted at fetch time |
| Donau2Space transience_of_dew CSV | Dummy placeholder data (sequential integers) |
| WeatherSpark history download | Paid/credits-gated |
| Kaggle weather datasets | Requires Kaggle auth; not pulled automatically |
| Tutiempo station downloads | Manual/interactive download flow |
| sensors.AFRICA Nairobi | Air quality, not dew-harvest labeled data |

## Label Caveat

`harvested_ml`/`wh_window` in derived weather datasets are **physics-informed estimates**, not measured dew yields. They are suitable for pipeline pretraining/sensitivity checks. D0.3 acceptance (≥15% net mL/Wh vs static, GroupKFold by `night_id`) must be proven on **real 14-night Nairobi bench telemetry**.
