# Ops Runbook

## Daily
- Check telemetry freshness, fault counts, bus voltage, harvest/Wh summary.
- Review critical alerts; respond using `docs/safety/FMEA.md`.

## Model/data
- Append night manifest/checksum. Run drift report before retrain.
- Promote model only via `python ml/promote_model.py ...`; prod requires measured D0.3 validity.

## Release
- CI green + golden pass + safety review + changelog/tag.
- OTA staged rollout with rollback armed.
