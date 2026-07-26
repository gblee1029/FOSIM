# SH-2 Fastening Optimizer MVP Design

## Objective

Create an executable CSV-based prototype that analyzes SH-2 fastening settings
and torque/speed/angle waveforms, simulates setting changes, and recommends
three candidate settings.

## User-Approved Scope

The current request explicitly skips approval gates and asks Phase 1 through
Phase 5 to be implemented continuously.

## Architecture

FastAPI owns import, validation, analysis, simulation, optimization, and SQLite
history. React/Vite owns the operator dashboard and calls backend APIs. The
backend services are split into small testable units.

## Data Flow

```text
settings CSV + waveform CSV
  -> validation
  -> preprocessing
  -> segmentation
  -> feature extraction
  -> diagnosis
  -> simulation
  -> candidate optimization
  -> ECharts overlay and candidate cards
```

## Safety

No real SH-2 write is implemented. Target Torque simulation displays warnings
and should require product torque limits before production use.

## Testing

Backend algorithms and API contract are covered by pytest. Frontend is verified
with TypeScript/Vite build and a Node utility check because Vitest config loading
hits a sandbox-specific esbuild parent-directory permission issue in this
workspace.
