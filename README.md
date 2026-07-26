# FOSIM

**Fastening Optimization & Simulation Manager**

FOSIM is an MVP desktop/web prototype for SH-2 Smart Manager fastening parameter analysis. It imports fastening settings and waveform CSV files, segments the waveform, extracts practical features, diagnoses common fastening patterns, simulates parameter changes in real time, and compares three candidate setting recommendations.

This MVP does **not** write settings to real SH-2 equipment.

## Implemented Scope

- Settings CSV import
- Torque, Speed, and Angle waveform CSV import
- Data validation and preprocessing
- Torque/Speed/Angle waveform viewer
- Engage, Seating, Target, Hold, and Stop markers
- Feature extraction
- Rule-based anomaly diagnosis
- Real-time simulation for:
  - Target Speed
  - Clamp Rising Time
  - Torque Hold Time
  - Target Torque
- Current/predicted waveform overlay
- Three optimization candidates:
  - Quality stable
  - Cycle time
  - Minimum change
- SQLite history tables
- Synthetic sample data
- Windows EXE packaging script

## Project Structure

```text
backend/
  app/
  tests/
frontend/
  src/
sample-data/
docs/
scripts/
```

## Run Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## Run Frontend

Open a second terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

The page loads a synthetic sample cycle automatically. You can also import:

- `sample-data/settings/normal-settings.csv`
- `sample-data/waveforms/normal-waveform.csv`

Move a slider or edit a number in the live setting editor to recalculate the predicted waveform automatically.

## Build Windows EXE

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

The script creates:

```text
outputs/FOSIM-exe.zip
```

Unzip it and run:

```text
FOSIM/FOSIM.exe
```

The EXE starts the local FastAPI server, serves the built React UI from the same process, and opens the browser automatically. Close the console window to stop the app.

## Tests

Backend:

```powershell
cd backend
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

## Sample Data

Generate sample CSV files again:

```powershell
python scripts/generate_sample_data.py
```

Synthetic samples are for pipeline and UI validation only. They are not measured SH-2 device data.

## Safety Note

The simulator is a rule-based what-if model. It can show the expected direction of change, but it does not guarantee real fastening behavior. Real SH-2 data and controlled before/after trials are required before production use.
