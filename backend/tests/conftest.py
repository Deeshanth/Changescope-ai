from pathlib import Path
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


@pytest.fixture()
def db_session(tmp_path: Path) -> Session:
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_fk(conn, _record):
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def sample_git_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    return repo_dir
