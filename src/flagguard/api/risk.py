"""Risk Prediction API Endpoint (Phase 2 — Step 2.4).

Exposes the XGBoost risk prediction model via a FastAPI REST endpoint.
The model is loaded once at import time for fast inference.

Endpoints:
    POST /api/v1/predict-risk  — Predict conflict risk + SHAP explanation
    GET  /api/v1/risk-model-info — Return model metadata
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from flagguard.core.logging import get_logger

logger = get_logger("api.risk")

router = APIRouter(tags=["Risk Prediction"])

# ── Pydantic Models ──


class RiskFeatures(BaseModel):
    """Input features for risk prediction.

    These correspond to the 14 features extracted from git commits
    by scripts/generate_training_data.py.
    """
    files_modified: int = Field(1, ge=0, description="Number of files changed")
    lines_added: int = Field(10, ge=0, description="Lines added in the commit")
    lines_deleted: int = Field(5, ge=0, description="Lines deleted in the commit")
    flag_mentions_count: int = Field(0, ge=0, description="Flag-related function calls in the diff")
    py_files_modified: int = Field(0, ge=0, description="Python files changed")
    js_files_modified: int = Field(0, ge=0, description="JS/TS files changed")
    config_files_modified: int = Field(0, ge=0, description="JSON/YAML config files changed")
    commit_hour: int = Field(12, ge=0, le=23, description="Hour of the commit (0-23)")
    is_merge_commit: int = Field(0, ge=0, le=1, description="1 if merge commit, 0 otherwise")
    message_length: int = Field(50, ge=0, description="Length of commit message")
    has_test_changes: int = Field(0, ge=0, le=1, description="1 if tests were modified")
    author_commit_count: int = Field(10, ge=0, description="Author's total commit count")
    days_since_last_commit: float = Field(1.0, ge=0, description="Days since last commit")
    diff_size_ratio: float = Field(0.5, ge=0, description="Deletion/addition ratio")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "files_modified": 12,
                    "lines_added": 250,
                    "lines_deleted": 80,
                    "flag_mentions_count": 5,
                    "py_files_modified": 4,
                    "js_files_modified": 0,
                    "config_files_modified": 2,
                    "commit_hour": 23,
                    "is_merge_commit": 0,
                    "message_length": 15,
                    "has_test_changes": 0,
                    "author_commit_count": 3,
                    "days_since_last_commit": 0.1,
                    "diff_size_ratio": 3.2,
                }
            ]
        }
    }


class ShapFactor(BaseModel):
    """A single SHAP factor explaining the prediction."""
    feature: str
    value: float
    impact: float
    direction: str


class RiskResponse(BaseModel):
    """Response from the risk prediction endpoint."""
    risk_score: float = Field(description="Probability of conflict (0.0-1.0)")
    risk_level: str = Field(description="Human-readable: low/medium/high/critical")
    prediction: int = Field(description="Binary: 0=safe, 1=risky")
    top_factors: list[ShapFactor] = Field(description="SHAP-based top contributing features")
    model_available: bool = Field(description="Whether the model is loaded")


class ModelInfoResponse(BaseModel):
    """Response from the model info endpoint."""
    model_type: str
    features: list[str]
    num_features: int
    is_available: bool
    has_shap: bool


# ── Lazy Model Loading ──

_explainer = None


def _get_explainer():
    """Lazily load the risk explainer (singleton)."""
    global _explainer
    if _explainer is None:
        try:
            from flagguard.ai.risk_explainer import RiskExplainer
            _explainer = RiskExplainer()
        except Exception as e:
            logger.error(f"Failed to load risk explainer: {e}")
            return None
    return _explainer


# ── Endpoints ──


@router.post(
    "/predict-risk",
    response_model=RiskResponse,
    summary="Predict conflict risk for a commit",
    description=(
        "Takes commit-level features (files modified, lines changed, flag mentions, etc.) "
        "and returns a risk score (0-1) with SHAP-based feature attributions explaining "
        "which factors are driving the prediction."
    ),
)
async def predict_risk(features: RiskFeatures) -> RiskResponse:
    """Predict conflict risk with SHAP explanation."""
    explainer = _get_explainer()

    if explainer is None or not explainer.is_available:
        raise HTTPException(
            status_code=503,
            detail=(
                "Risk prediction model not available. "
                "Train it first: python notebooks/train_risk_model.py"
            ),
        )

    # Convert Pydantic model to dict
    feature_dict = features.model_dump()

    # Predict
    result = explainer.predict_and_explain(feature_dict)

    return RiskResponse(
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        prediction=result.prediction,
        top_factors=[ShapFactor(**f) for f in result.top_factors],
        model_available=True,
    )


@router.get(
    "/risk-model-info",
    response_model=ModelInfoResponse,
    summary="Get model metadata",
    description="Returns information about the loaded risk prediction model.",
)
async def risk_model_info() -> ModelInfoResponse:
    """Return model metadata."""
    explainer = _get_explainer()

    if explainer is None:
        return ModelInfoResponse(
            model_type="XGBClassifier",
            features=[],
            num_features=0,
            is_available=False,
            has_shap=False,
        )

    info = explainer.get_model_info()
    return ModelInfoResponse(**info)
