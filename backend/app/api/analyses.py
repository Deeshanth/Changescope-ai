from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AIServiceUnavailableError,
    AnalysisNotFoundError,
    GitOperationError,
    InvalidRepositoryError,
    PathAccessDeniedError,
    RepositoryNotFoundError,
)
from app.db.database import get_db
from app.db.models import AIReport, AnalysisRun, CodeNode, ImpactedComponent, RepoFile, Repository
from app.schemas.ai_report import AIReportRequest, AIReportResponse, RecommendedTestItem
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisRunDetailResponse,
    AnalysisRunSummaryResponse,
    ImpactedComponentResponse,
)
from app.services.ai_service import AIService
from app.services.impact_service import ImpactService

router = APIRouter(tags=["analyses"])
_impact_service = ImpactService()
_ai_service = AIService()


def _serialize_run_detail(db: Session, run: AnalysisRun) -> AnalysisRunDetailResponse:
    impacts = (
        db.query(ImpactedComponent, CodeNode, RepoFile)
        .join(CodeNode, ImpactedComponent.node_id == CodeNode.id)
        .join(RepoFile, CodeNode.file_id == RepoFile.id)
        .filter(ImpactedComponent.analysis_run_id == run.id)
        .order_by(ImpactedComponent.risk_score.desc(), ImpactedComponent.hop_distance.asc())
        .all()
    )

    components = [
        ImpactedComponentResponse(
            id=imp.id,
            node_id=node.id,
            node_key=node.node_key,
            node_type=node.node_type,
            name=node.name,
            file_path=rfile.file_path,
            start_line=node.start_line,
            end_line=node.end_line,
            is_test=node.is_test,
            impact_type=imp.impact_type,
            hop_distance=imp.hop_distance,
            risk_score=imp.risk_score,
            risk_level=imp.risk_level,
            risk_factors=imp.risk_factors_json,
            dependency_paths=imp.dependency_paths_json,
        )
        for imp, node, rfile in impacts
    ]

    return AnalysisRunDetailResponse(
        id=run.id,
        repo_id=run.repo_id,
        base_commit=run.base_commit,
        head_commit=run.head_commit,
        overall_risk_score=run.overall_risk_score,
        risk_level=run.risk_level,
        summary_json=run.summary_json,
        status=run.status,
        created_at=run.created_at,
        impacted_components=components,
        has_ai_report=run.ai_report is not None,
    )


def _serialize_ai_report(report: AIReport) -> AIReportResponse:
    return AIReportResponse(
        id=report.id,
        analysis_run_id=report.analysis_run_id,
        model_name=report.model_name,
        explanation_markdown=report.explanation_markdown,
        recommended_tests=[
            RecommendedTestItem(**item) for item in (report.recommended_tests_json or [])
        ],
        prompt_tokens=report.prompt_tokens,
        completion_tokens=report.completion_tokens,
        created_at=report.created_at,
    )


@router.post(
    "/repositories/{repo_id}/analyses",
    response_model=AnalysisRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_impact_analysis(
    repo_id: int,
    payload: AnalysisCreateRequest,
    db: Session = Depends(get_db),
) -> AnalysisRunDetailResponse:
    try:
        run = _impact_service.run_analysis(
            db,
            repo_id=repo_id,
            base_commit=payload.base_commit,
            head_commit=payload.head_commit,
            max_depth=payload.max_depth,
        )
        return _serialize_run_detail(db, run)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PathAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InvalidRepositoryError, GitOperationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/repositories/{repo_id}/analyses",
    response_model=List[AnalysisRunSummaryResponse],
)
def list_analyses(repo_id: int, db: Session = Depends(get_db)) -> List[AnalysisRunSummaryResponse]:
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    runs = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.repo_id == repo_id)
        .order_by(AnalysisRun.created_at.desc())
        .all()
    )
    return [AnalysisRunSummaryResponse.model_validate(r) for r in runs]


@router.get("/analyses/{analysis_id}", response_model=AnalysisRunDetailResponse)
def get_analysis_detail(analysis_id: int, db: Session = Depends(get_db)) -> AnalysisRunDetailResponse:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")
    return _serialize_run_detail(db, run)


@router.get("/analyses/{analysis_id}/ai-report", response_model=AIReportResponse)
def get_ai_report(analysis_id: int, db: Session = Depends(get_db)) -> AIReportResponse:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")
    report = _ai_service.get_report(db, analysis_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI report not generated yet.")
    return _serialize_ai_report(report)


@router.post("/analyses/{analysis_id}/ai-report", response_model=AIReportResponse)
def generate_ai_report(
    analysis_id: int,
    payload: AIReportRequest = AIReportRequest(),
    db: Session = Depends(get_db),
) -> AIReportResponse:
    try:
        report = _ai_service.generate_report(
            db, analysis_run_id=analysis_id, regenerate=payload.regenerate
        )
        return _serialize_ai_report(report)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AIServiceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
