from dataclasses import dataclass
import math
from typing import Any, Dict, List


@dataclass(frozen=True)
class ComponentRiskInput:
    node_id: int
    node_key: str
    node_type: str
    is_test: bool
    hop_distance: int
    fan_in: int
    complexity: int
    loc: int
    changed_lines: int
    has_heuristic_path: bool
    max_repo_fan_in: int


@dataclass(frozen=True)
class ComponentRiskResult:
    risk_score: float
    risk_level: str
    factors: Dict[str, Any]


def classify_risk_level(score: float) -> str:
    if score >= 75.0:
        return "CRITICAL"
    if score >= 50.0:
        return "HIGH"
    if score >= 25.0:
        return "MEDIUM"
    return "LOW"


class RiskEngine:
    """
    100% deterministic, explainable risk calculation engine.
    Every score is derived purely from structural metrics, change size, and graph proximity.
    """

    MAX_PROXIMITY_WEIGHT = 35.0
    MAX_CENTRALITY_WEIGHT = 25.0
    MAX_CHURN_WEIGHT = 20.0
    MAX_COMPLEXITY_WEIGHT = 15.0
    MAX_UNCERTAINTY_WEIGHT = 5.0
    TEST_NODE_DAMPENING = 0.35

    def calculate_component_risk(self, item: ComponentRiskInput) -> ComponentRiskResult:
        proximity_pts = round(self.MAX_PROXIMITY_WEIGHT * (0.65 ** item.hop_distance), 2)

        norm_denom = math.log1p(max(item.max_repo_fan_in, 10))
        centrality_ratio = min(1.0, math.log1p(max(0, item.fan_in)) / norm_denom)
        centrality_pts = round(self.MAX_CENTRALITY_WEIGHT * centrality_ratio, 2)

        safe_loc = max(1, item.loc)
        if item.hop_distance == 0:
            churn_ratio = min(1.0, max(0, item.changed_lines) / safe_loc)
            if item.changed_lines > 0:
                churn_ratio = max(churn_ratio, 0.25)
            churn_pts = round(self.MAX_CHURN_WEIGHT * churn_ratio, 2)
        else:
            churn_pts = round(self.MAX_CHURN_WEIGHT * 0.25 / item.hop_distance, 2)

        complexity_ratio = min(1.0, max(0, item.complexity - 1) / 15.0)
        complexity_pts = round(self.MAX_COMPLEXITY_WEIGHT * complexity_ratio, 2)

        uncertainty_pts = self.MAX_UNCERTAINTY_WEIGHT if item.has_heuristic_path else 0.0

        raw_score = proximity_pts + centrality_pts + churn_pts + complexity_pts + uncertainty_pts
        dampening = self.TEST_NODE_DAMPENING if item.is_test else 1.0
        final_score = round(min(100.0, max(0.0, raw_score * dampening)), 2)

        factors = {
            "proximity_score": proximity_pts,
            "proximity_max": self.MAX_PROXIMITY_WEIGHT,
            "centrality_score": centrality_pts,
            "centrality_max": self.MAX_CENTRALITY_WEIGHT,
            "churn_score": churn_pts,
            "churn_max": self.MAX_CHURN_WEIGHT,
            "complexity_score": complexity_pts,
            "complexity_max": self.MAX_COMPLEXITY_WEIGHT,
            "uncertainty_penalty": uncertainty_pts,
            "uncertainty_max": self.MAX_UNCERTAINTY_WEIGHT,
            "raw_score": round(raw_score, 2),
            "test_dampening_factor": dampening,
            "inputs": {
                "hop_distance": item.hop_distance,
                "fan_in": item.fan_in,
                "complexity": item.complexity,
                "changed_lines": item.changed_lines,
                "symbol_loc": safe_loc,
                "is_test": item.is_test,
                "has_heuristic_path": item.has_heuristic_path,
            },
        }

        return ComponentRiskResult(
            risk_score=final_score,
            risk_level=classify_risk_level(final_score),
            factors=factors,
        )

    def calculate_overall_risk(
        self, component_results: List[tuple[bool, float]]
    ) -> tuple[float, str, Dict[str, Any]]:
        if not component_results:
            return (
                0.0,
                "LOW",
                {
                    "peak_risk": 0.0,
                    "top5_average_risk": 0.0,
                    "blast_breadth_score": 0.0,
                    "non_test_impacted_count": 0,
                },
            )

        non_test_scores = sorted(
            (score for is_test, score in component_results if not is_test),
            reverse=True,
        )
        all_scores = sorted((score for _, score in component_results), reverse=True)
        active_scores = non_test_scores if non_test_scores else all_scores

        peak_risk = active_scores[0]
        top5 = active_scores[:5]
        top5_avg = sum(top5) / len(top5)
        blast_breadth = min(100.0, len(non_test_scores) * 8.0)

        overall = round(
            min(100.0, 0.50 * peak_risk + 0.30 * top5_avg + 0.20 * blast_breadth),
            2,
        )

        breakdown = {
            "peak_risk": round(peak_risk, 2),
            "top5_average_risk": round(top5_avg, 2),
            "blast_breadth_score": round(blast_breadth, 2),
            "non_test_impacted_count": len(non_test_scores),
            "weights": {"peak": 0.50, "top5_avg": 0.30, "breadth": 0.20},
        }
        return (overall, classify_risk_level(overall), breakdown)
