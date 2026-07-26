# SH-2 Fastening Optimizer MVP Architecture

## Goal

Build a CSV-based prototype that analyzes SH-2 fastening waveforms, simulates
setting changes, and recommends three safe candidate settings without writing to
real SH-2 hardware.

## Scope

Implemented MVP phases:

1. Phase 1 design documents and data contracts.
2. Backend and frontend project scaffolding.
3. CSV import, validation, waveform analysis, and viewer support.
4. Rule-based segmentation, feature extraction, and diagnosis.
5. Rule-based waveform simulation for Target Speed, Clamp Rising Time, Torque
   Hold Time, and Target Torque.

Out of scope:

- Real SH-2 USB/RS485 communication.
- Smart Manager automation.
- PLC integration.
- Production automatic write-back.
- Deep learning waveform prediction.

## Components

```text
CSV files
  -> FastAPI import service
  -> preprocessing
  -> segmentation
  -> feature extraction
  -> rule diagnosis
  -> simulation engine
  -> optimization engine
  -> React dashboard
```

## Backend

- `app/services/import_service`: reads settings and waveform CSV text.
- `app/services/preprocessing`: sorts samples, removes duplicates, interpolates
  optional channels, calculates sampling interval.
- `app/services/segmentation`: detects Start, Free Run, Engage, Seating, Clamp,
  Hold, and Stop markers.
- `app/services/feature_extraction`: calculates torque, speed, angle, clamp,
  seating, hold, overshoot, and stability features.
- `app/services/diagnosis`: maps features to rule-based anomaly diagnoses.
- `app/services/simulation`: estimates changed features and reconstructs a
  predicted waveform.
- `app/services/optimization`: generates candidates, applies constraints, scores
  candidates, and returns quality, cycle-time, and minimum-change recommendations.
- `app/db`: stores imported cycles, settings, analyses, simulations, and
  optimization runs in SQLite.

## Frontend

The React UI uses an operational dashboard layout:

- import panel for settings/waveform CSV files,
- waveform chart with current/predicted overlays,
- feature and diagnosis panels,
- setting editor for four MVP variables,
- candidate comparison cards.

The UI uses local shadcn-style primitives in `components/ui`, Tailwind CSS, and
ECharts.
