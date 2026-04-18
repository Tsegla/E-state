from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Callable

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


@pytest.fixture()
def session_factory() -> Iterator[Callable[[], Session]]:
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    yield Local
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def session(session_factory) -> Iterator[Session]:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()
