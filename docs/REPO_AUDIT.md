# Repo Audit & Reorg Plan

## Current State (what we have)

- **Strong**: D0.1 docs (BOM/wiring/calibration/runbook), working ESP32-S3 firmware build, logger, leak-free ML pipeline (GroupKFold by `night_id`), 47-county 2023-24 weather data, edge policy artifacts, software demo, deployment script.
- **Weak/messy**: large data/artifacts mixed in repo (1.4G `ml/`), duplicate firmware headers (`config.h`/`dewleaf_policy.h` in root and `src/`), generated models/artifacts committed ad hoc, no tests/CI/ADR/schema/contracts, no hardware bringup test plan, no data/model registry, no clear separation of source vs generated vs external data, no security/licensing/release process.

## Reference patterns (observed)

- Embedded/TinyML repos separate `docs/`, `hardware/`, `firmware/`, `ml/` (dataset/training/model/testing), `app/`, tests, and tooling. (Gnss-rainfall-detection-tinyML)
- Mature systems repos separate product code, tests by ladder (unit/smoke/integration/sweep/perf/e2e), tools/scripts, docs, ownership/contracts, CI, ADRs. (TT-Metal/accelerator blueprint)
- Firmware repos separate `common/`, platform/HAL, board BSP, drivers, app, storage/comm/intelligence. (EsoCore)
- Microcontroller bases separate `src`, `lib`, `include`, `docs`, wiring/BOM, tests. (microcontroller-base)

## Target Structure

```text
BIGTHING/
  README.md
  AGENTS.md
  LICENSE
  .gitignore
  .env.example
  Makefile
  docs/
    adr/
    architecture/
    hardware/
    firmware/
    ml/
    ops/
    reports/
  hardware/
    bom/
    wiring/
    mechanical/
    calibration/
    bringup/
  firmware/
    dewleaf_node/
      platformio.ini
      include/
      src/
      lib/
      test/
    shared/
  ml/
    data/
      raw/              # gitignored/externally stored
      processed/        # gitignored/generated
      external/         # manifests/provenance only
    datasets/
      schemas/
      manifests/
    features/
    training/
    evaluation/
    export/
    models/
      registry/
      cards/
    notebooks/          # optional, reviewed
  edge/
    policy/
    simulator/
  software/
    logger/
    cloud/
    tools/
  tests/
    unit/
    integration/
    hardware/
    data/
    e2e/
  scripts/
  .github/workflows/
```

## Gap Matrix (deeper)

| Area | Current | Missing | Priority |
|---|---|---|---|
| System contracts | implicit CSV/header behavior | versioned schemas for telemetry, dataset, model artifact, API | P0 |
| Hardware bringup | docs only | stepwise bringup checklist, test fixtures, pass/fail logs, calibration records | P0 |
| Firmware quality | builds, basic logic | unit tests (native), HIL smoke, fault injection, config validation, OTA/update plan | P0 |
| Data governance | big local CSVs | raw/processed split, provenance, checksums, dataset card, PII/license checks | P0 |
| ML rigor | GroupKFold by night | baseline defs, ablation, calibration, uncertainty, drift, leakage tests, model card, registry | P0 |
| Edge deployment | heuristic + exported forests | TFLM/quantized model path, latency/RAM/flash budget tests, golden vectors | P1 |
| Observability | CSV logs | structured events, metrics, alerts, device health, OTA-safe logging | P1 |
| Security/safety | basic interlocks | threat model, secret handling, signed artifacts, actuator fail-safe matrix, watchdog/fault taxonomy | P1 |
| Ops/release | script | CI, release checklist, versioning, reproducible env, artifact storage | P1 |
| Field validation | simulated demo | real 14-night protocol, labeled anomalies, agronomic/water balance audit trail | P0 |

## Immediate Cleanup (safe)

1. Move generated large data under `ml/data/` gitignored raw/processed; keep manifests.
2. Remove duplicate firmware headers; single source in `include/` or `src/`.
3. Add schemas/contracts for telemetry row, dataset row, model report.
4. Add tests: data schema, feature determinism, GroupKFold no-leak, policy safety.
5. Add ADRs for dual-rail power, ADC1-only, reward objective, edge model format.
6. Add Makefile targets: `setup`, `lint`, `test`, `sim`, `train`, `build-fw`.
