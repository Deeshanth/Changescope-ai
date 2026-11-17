from pathlib import Path
import subprocess
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import get_db
from app.db.models import Base
from app.main import app


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), capture_output=True, check=True)


@pytest.fixture()
def api_client(tmp_path: Path) -> TestClient:
    db_file = tmp_path / "api_test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk(conn, _rec):
        conn.cursor().execute("PRAGMA foreign_keys=ON;")

    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_register_scan_and_list_files_and_commits(api_client: TestClient, tmp_path: Path) -> None:
    repo = tmp_path / "demo_py"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")

    (repo / "core.py").write_text("def core_fn():\n    return 42\n", encoding="utf-8")
    (repo / "api.py").write_text("from core import core_fn\n\ndef endpoint():\n    return core_fn()\n", encoding="utf-8")
    (repo / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial codebase")

    res = api_client.post("/api/repositories", json={"local_path": str(repo)})
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "ready"
    assert data["stats"]["file_count"] == 3
    assert data["stats"]["parse_error_count"] == 1
    assert data["stats"]["edge_count"] >= 2

    repo_id = data["id"]
    files_res = api_client.get(f"/api/repositories/{repo_id}/files")
    assert files_res.status_code == 200
    assert len(files_res.json()) == 3

    commits_res = api_client.get(f"/api/repositories/{repo_id}/commits")
    assert commits_res.status_code == 200
    assert commits_res.json()[0]["subject"] == "initial codebase"
