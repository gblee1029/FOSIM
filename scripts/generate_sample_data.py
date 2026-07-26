from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.import_service.sample_data import write_sample_files


if __name__ == "__main__":
    write_sample_files(PROJECT_ROOT)
    print(f"Sample data written under {PROJECT_ROOT / 'sample-data'}")
