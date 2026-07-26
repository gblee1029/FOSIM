from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.paths import frontend_dist_path
from app.db.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="SH-2 Fastening Optimizer Prototype",
        version="0.1.0",
        description="CSV-based MVP for SH-2 waveform analysis, simulation, and setting optimization.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    init_db()
    app.include_router(router, prefix="/api")
    mount_frontend(app)
    return app


def mount_frontend(app: FastAPI) -> None:
    dist_path = frontend_dist_path()
    index_path = dist_path / "index.html"
    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    if index_path.exists():
        @app.get("/", include_in_schema=False)
        def serve_index() -> FileResponse:
            return FileResponse(index_path)

        @app.get("/{path:path}", include_in_schema=False)
        def serve_spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                # API 404s should remain API 404s, not the React app.
                raise HTTPException(status_code=404, detail="API route not found")
            return FileResponse(index_path)


app = create_app()
