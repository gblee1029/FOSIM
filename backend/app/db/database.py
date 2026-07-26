from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.paths import runtime_data_dir
from app.db.models import Base


DATA_DIR = runtime_data_dir()
DATABASE_URL = f"sqlite:///{DATA_DIR / 'sh2_optimizer.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
