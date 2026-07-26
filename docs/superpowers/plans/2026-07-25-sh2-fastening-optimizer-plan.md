# SH-2 Fastening Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an executable SH-2 CSV-based waveform analysis, simulation, and setting recommendation prototype.

**Architecture:** Backend services are pure, testable Python units exposed through FastAPI. Frontend is a Vite React dashboard that consumes those APIs and renders ECharts overlays. SQLite stores MVP history records.

**Tech Stack:** Python FastAPI, pandas, NumPy, SQLAlchemy, SQLite, pytest, React, TypeScript, Vite, Tailwind CSS, ECharts.

## Global Constraints

- No real SH-2 communication or setting write in this MVP.
- Use synthetic sample data.
- Implement Phase 1 through Phase 5 without waiting for additional approval.
- Include README, scripts, tests, and limitations.

---

### Task 1: Backend Analysis Core

**Files:**
- Create: `backend/app/services/segmentation/segments.py`
- Create: `backend/app/services/feature_extraction/features.py`
- Create: `backend/tests/test_analysis_pipeline.py`

**Interfaces:**
- Produces: `detect_segments(waveform, settings)`
- Produces: `extract_features(waveform, segments, settings)`

- [x] Write failing tests for segmentation and feature extraction.
- [x] Run pytest and confirm missing modules fail.
- [x] Implement rule-based segmentation and feature extraction.
- [x] Run pytest and confirm tests pass.

### Task 2: Simulation and Optimization

**Files:**
- Create: `backend/app/services/simulation/simulator.py`
- Create: `backend/app/services/optimization/optimizer.py`
- Modify: `backend/tests/test_analysis_pipeline.py`

**Interfaces:**
- Produces: `simulate_waveform(...)`
- Produces: `optimize_candidates(...)`

- [x] Write failing tests for simulation and candidate selection.
- [x] Implement rule-based feature prediction and waveform reconstruction.
- [x] Implement candidate generation, constraints, score, and three labels.
- [x] Run pytest and confirm tests pass.

### Task 3: API and SQLite

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/app/db/models.py`
- Create: `backend/tests/test_api_contract.py`

**Interfaces:**
- Produces: `/api/import/csv`
- Produces: `/api/simulations`
- Produces: `/api/optimizations`

- [x] Write failing API flow test.
- [x] Implement import, analysis, simulation, and optimization endpoints.
- [x] Add SQLite tables and history inserts.
- [x] Run pytest and confirm tests pass.

### Task 4: Frontend Dashboard

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/WaveformChart.tsx`
- Create: `frontend/src/components/SettingsPanel.tsx`
- Create: `frontend/src/components/CandidateCards.tsx`

**Interfaces:**
- Consumes backend API payloads.
- Produces interactive import, chart, simulation, and candidate comparison UI.

- [x] Create Vite/React/Tailwind scaffold.
- [x] Add API client and TypeScript domain types.
- [x] Add chart, panels, and candidate comparison UI.
- [x] Run frontend build.

### Task 5: Documentation and Packaging

**Files:**
- Create: `README.md`
- Create: `docs/*.md`
- Create: `scripts/*.ps1`
- Create: output zip

- [x] Add architecture, schema, simulation, optimization, and limitations docs.
- [x] Add run scripts.
- [x] Run backend tests and frontend build/test.
- [ ] Create final zip.
