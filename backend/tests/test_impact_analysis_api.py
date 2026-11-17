from pathlib import Path
import subprocess
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import get_db
from app.db.models import Base
from app.main import app


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return proc.stdout.strip()


@pytest.fixture()
def analysis_client(tmp_path: Path) -> TestClient:
    db_file = tmp_path / "impact_test.db"
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


def test_end_to_end_deterministic_impact_traversal(analysis_client: TestClient, tmp_path: Path) -> None:
    repo = tmp_path / "impact_repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")

    (repo / "pricing.py").write_text(
        "def compute_tax(amount):\n    return amount * 0.1\n",
        encoding="utf-8",
    )
    (repo / "checkout.py").write_text(
        "from pricing import compute_tax\n\ndef total_price(amount):\n    return amount + compute_tax(amount)\n",
        encoding="utf-8",
    )
    (repo / "routes.py").write_text(
        "from checkout import total_price\n\ndef pay(amount):\n    return total_price(amount)\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "v1")
    c1 = _git(repo, "rev-parse", "HEAD")

    (repo / "pricing.py").write_text(
        "def compute_tax(amount):\n    if amount > 100:\n        return amount * 0.15\n    return amount * 0.1\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "update tax tiers")
    c2 = _git(repo, "rev-parse", "HEAD")

    reg = analysis_client.post("/api/repositories", json={"local_path": str(repo)})
    assert reg.status_code == 201
    repo_id = reg.json()["id"]

    res = analysis_client.post(
        f"/api/repositories/{repo_id}/analyses",
        json={"base_commit": c1, "head_commit": c2, "max_depth": 5},
    )
    assert res.status_code == 201
    report = res.json()

    impacted_by_key = {c["node_key"]: c for c in report["impacted_components"]}
    assert impacted_by_key["pricing.compute_tax"]["impact_type"] == "direct"
    assert impacted_by_key["pricing.compute_tax"]["hop_distance"] == 0

    assert impacted_by_key["checkout.total_price"]["impact_type"] == "transitive"
    assert impacted_by_key["checkout.total_price"]["hop_distance"] == 1

    assert impacted_by_key["routes.pay"]["impact_type"] == "transitive"
    assert impacted_by_key["routes.pay"]["hop_distance"] == 2
    assert ["pricing.compute_tax", "checkout.total_price", "routes.pay"] in impacted_by_key["routes.pay"]["dependency_paths"]
