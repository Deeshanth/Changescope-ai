from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreateRequest(BaseModel):
    base_commit: str = Field(..., min_length=1, max_length=64)
    head_commit: str = Field(..., min_length=1, max_length=64)
    max_depth: int = Field(5, ge=1, le=8)


class ImpactedComponentResponse(BaseModel):
    id: int
    node_id: int
    node_key: str
    node_type: str
    name: str
    file_path: str
    start_line: int
    end_line: int
    is_test: bool
    impact_type: str
    hop_distance: int
    risk_score: float
    risk_level: str
    risk_factors: Dict[str, Any]
    dependency_paths: List[List[str]]


class AnalysisRunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: int
    base_commit: str
    head_commit: str
    overall_risk_score: float
    risk_level: str
    summary_json: Dict[str, Any]
    status: str
    created_at: datetime


class AnalysisRunDetailResponse(AnalysisRunSummaryResponse):
    impacted_components: List[ImpactedComponentResponse]
    has_ai_report: bool = False
