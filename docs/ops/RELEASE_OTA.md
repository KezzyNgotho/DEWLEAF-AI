# Release & OTA (Design)

## Release artifacts
- Firmware: PlatformIO build + SHA256 + git tag + changelog entry.
- Model: header/tflite + report + golden vectors + registry entry.
- Sign artifacts before distribution (future: cosign/sigstore).

## OTA strategy (ESP32-S3)
- Use A/B app partitions; boot known-good on failure.
- Staged rollout: bench -> 1 device -> cohort -> fleet.
- Rollback trigger: boot loop, critical fault spike, telemetry loss, mL/Wh regression.
- Never OTA without: passing CI, golden baseline, model registry promotion gate, explicit release note.

## Promotion gates
- `dev`: tests pass.
- `staging`: tests + golden + data contract + replay on sample.
- `prod`: staging + `measured_data=true` + D0.3 claim valid + safety review.
