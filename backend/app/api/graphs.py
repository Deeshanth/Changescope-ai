from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryNotFoundError
from app.db.database import get_db
from app.schemas.graph import GraphViewResponse, RepoOverviewResponse
from app.services.graph_service import GraphService

router = APIRouter(prefix="/repositories/{repo_id}", tags=["graphs"])
_graph_service = GraphService()


@router.get("/overview", response_model=RepoOverviewResponse)
def get_repository_overview(repo_id: int, db: Session = Depends(get_db)) -> RepoOverviewResponse:
    try:
        metrics = _graph_service.get_overview_metrics(db, repo_id)
        return RepoOverviewResponse(**metrics)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/graph", response_model=GraphViewResponse)
def get_repository_graph(
    repo_id: int,
    level: str = Query("symbol", pattern="^(symbol|module)$"),
    node_type: Optional[str] = Query(None, pattern="^(module|class|function|method)$"),
    focus_node_id: Optional[int] = Query(None),
    depth: int = Query(2, ge=1, le=4),
    include_tests: bool = Query(True),
    limit: int = Query(250, ge=10, le=1000),
    db: Session = Depends(get_db),
) -> GraphViewResponse:
    try:
        data = _graph_service.get_graph_view(
            db,
            repo_id=repo_id,
            level=level,
            node_type=node_type,
            focus_node_id=focus_node_id,
            depth=depth,
            include_tests=include_tests,
            limit=limit,
        )
        return GraphViewResponse(**data)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/nodes/{node_id}")
def get_node_details(repo_id: int, node_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        details = _graph_service.get_node_neighborhood(db, repo_id, node_id)
        if not details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found.")
        return details
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
