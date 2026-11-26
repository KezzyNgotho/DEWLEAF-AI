# Cloud / Telemetry Scaffold (Phase 1+)

Phase 0 runs offline on the bench rig. This scaffold defines the Phase 1+ ingestion contract.

## Planned Components

- **FastAPI** ingestion endpoint for daily GSM JSON payloads.
- **PostgreSQL** telemetry store: device, night, action, sensor, energy, water balance.
- **SMS alerts**: low tank, sensor fault, frost guard, flow anomaly.
- **Dashboard**: Dew L + Rain L vs Crop ET L, mL/Wh, yield forecast.

## Daily Payload Contract (draft)

```json
{
  "device_id": "dewleaf-node1-bench",
  "date": "2026-01-01",
  "night_id": "night-20260101",
  "dew_l": 3.5,
  "rain_l": 0.0,
  "irrigation_l": 12.0,
  "wh_used": 24.2,
  "avg_soil_pct": 64.1,
  "alerts": []
}
```
