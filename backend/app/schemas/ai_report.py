from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class RecommendedTestItem(BaseModel):
    target_component: str
    test_type: str
    priority: str
    rationale: str
    suggested_scenario: str


class AIReportRequest(BaseModel):
    regenerate: bool = False


class AIReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_run_id: int
    model_name: str
    explanation_markdown: str
    recommended_tests: List[RecommendedTestItem]
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime
