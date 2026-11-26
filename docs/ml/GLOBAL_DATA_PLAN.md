# Global Data Plan

## Goal
Pretrain DewLeaf policy on diverse climates, then calibrate on real Nairobi bench telemetry.

## Sources
- Open-Meteo ERA5 archive (no key, CC-BY 4.0): global hourly weather.
- Future: NASA POWER, ERA5/CHIRPS, local station CSVs, real bench logs.

## Current Global Pull
- `ml/data/global_open_meteo/2024/`: 38 locations across Africa, Middle East, South Asia, East Asia, Americas, Europe, Australia.
- Derived: `ml/data/dewleaf_global_2024_v2.csv` (~874k rows).
- Report: `ml/artifacts/global_2024_report.json` (120k sampled, GroupKFold night_id, synthetic labels).

## Caveats
- Weather is real; harvested/Wh labels are physics-informed synthetic.
- Timezone normalized to UTC in global fetch; night_id uses local-window heuristic - validate before production.
- Disk budget: avoid unbounded pulls; prefer yearly chunks and manifests.
