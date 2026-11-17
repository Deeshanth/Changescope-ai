import json
from types import SimpleNamespace
import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AIServiceUnavailableError
from app.db.models import AnalysisRun, CodeNode, ImpactedComponent, RepoFile, Repository
from app.services.ai_service import AIService


def _seed_analysis(db: Session) -> AnalysisRun:
    repo = Repository(name="ai_demo", local_path="/tmp/ai_demo", status="ready")
    db.add(repo)
    db.flush()

    f = RepoFile(repo_id=repo.id, file_path="billing.py", loc=30)
    db.add(f)
    db.flush()

    node = CodeNode(
        repo_id=repo.id,
        file_id=f.id,
        node_key="billing.charge",
        node_type="function",
        name="charge",
        qualified_name="billing.charge",
        start_line=1,
        end_line=20,
        complexity=5,
        fan_in=4,
    )
    db.add(node)
    db.flush()

    run = AnalysisRun(
        repo_id=repo.id,
        base_commit="aaa111",
        head_commit="bbb222",
        overall_risk_score=68.5,
        risk_level="HIGH",
        summary_json={"direct_impact_count": 1, "transitive_impact_count": 0},
    )
    db.add(run)
    db.flush()

    db.add(
        ImpactedComponent(
            analysis_run_id=run.id,
            node_id=node.id,
            impact_type="direct",
            hop_distance=0,
            risk_score=68.5,
            risk_level="HIGH",
            risk_factors_json={"proximity_score": 35.0},
            dependency_paths_json=[["billing.charge"]],
        )
    )
    db.commit()
    db.refresh(run)
    return run


def test_ai_service_raises_when_unconfigured(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _seed_analysis(db_session)
    monkeypatch.setattr(settings, "anthropic_api_key", None)

    service = AIService()
    with pytest.raises(AIServiceUnavailableError):
        service.generate_report(db_session, run.id)


def test_ai_service_generates_and_persists_report_without_altering_risk(db_session: Session) -> None:
    run = _seed_analysis(db_session)

    fake_json = json.dumps(
        {
            "explanation_markdown": "## Impact Summary\n`billing.charge` has 4 callers.",
            "recommended_tests": [
                {
                    "target_component": "billing.charge",
                    "test_type": "unit",
                    "priority": "HIGH",
                    "rationale": "Direct modification to payment charging logic.",
                    "suggested_scenario": "Verify idempotency and negative amount rejection.",
                }
            ],
        }
    )

    class _FakeMessages:
        def create(self, **_kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=fake_json)],
                usage=SimpleNamespace(input_tokens=120, output_tokens=85),
            )

    fake_client = SimpleNamespace(messages=_FakeMessages())
    service = AIService(client=fake_client)

    report = service.generate_report(db_session, run.id)
    assert report.analysis_run_id == run.id
    assert "billing.charge" in report.explanation_markdown
    assert len(report.recommended_tests_json) == 1
    assert report.prompt_tokens == 120

    db_session.refresh(run)
    assert run.overall_risk_score == 68.5
