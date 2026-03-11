"""SHAP-based Risk Explainer for FlagGuard (Phase 2 — Step 2.3).

Provides interpretable explanations for XGBoost risk predictions
using SHAP (SHapley Additive exPlanations) TreeExplainer.

Features:
    - Load trained XGBoost model from joblib
    - Compute SHAP values for individual predictions
    - Generate waterfall plots (saved as PNG)
    - Return top contributing features with direction and magnitude

Skills demonstrated: SHAP, XGBoost, Explainable AI (XAI), matplotlib.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flagguard.core.logging import get_logger

logger = get_logger("ai.risk_explainer")

# Default paths
DEFAULT_MODEL_PATH = "models/risk_model.joblib"
DEFAULT_META_PATH = "models/risk_model_meta.json"


@dataclass
class RiskPrediction:
    """Result of a risk prediction with SHAP explanation."""
    risk_score: float  # 0.0 to 1.0 probability
    risk_level: str  # "low", "medium", "high", "critical"
    prediction: int  # 0 or 1
    top_factors: list[dict] = field(default_factory=list)  # [{feature, value, impact, direction}]
    shap_values: list[float] = field(default_factory=list)
    shap_base_value: float = 0.0
    waterfall_plot_path: str | None = None


def _risk_level(score: float) -> str:
    """Map a risk score (0-1) to a human-readable level."""
    if score < 0.25:
        return "low"
    elif score < 0.50:
        return "medium"
    elif score < 0.75:
        return "high"
    return "critical"


class RiskExplainer:
    """SHAP-based explainer for the XGBoost risk prediction model.

    Loads a trained model and uses SHAP TreeExplainer to generate
    interpretable risk explanations.

    Usage:
        >>> explainer = RiskExplainer("models/risk_model.joblib")
        >>> result = explainer.predict_and_explain({
        ...     "files_modified": 12,
        ...     "lines_added": 250,
        ...     "flag_mentions_count": 5,
        ...     ...
        ... })
        >>> print(result.risk_score)  # 0.82
        >>> print(result.risk_level)  # "high"
        >>> print(result.top_factors[0])  # {"feature": "flag_mentions_count", ...}
    """

    FEATURE_NAMES = [
        "files_modified",
        "lines_added",
        "lines_deleted",
        "flag_mentions_count",
        "py_files_modified",
        "js_files_modified",
        "config_files_modified",
        "commit_hour",
        "is_merge_commit",
        "message_length",
        "has_test_changes",
        "author_commit_count",
        "days_since_last_commit",
        "diff_size_ratio",
    ]

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        """Initialize the SHAP explainer.

        Args:
            model_path: Path to the trained .joblib model file.
        """
        self.model = None
        self.explainer = None
        self.feature_names = list(self.FEATURE_NAMES)
        self.is_available = False

        self._load_model(model_path)

    def _load_model(self, model_path: str):
        """Load the XGBoost model and initialize SHAP explainer."""
        try:
            import joblib
            import numpy as np

            if not Path(model_path).exists():
                logger.warning(f"Model not found at {model_path}")
                return

            self.model = joblib.load(model_path)

            # Load feature names from metadata if available
            meta_path = model_path.replace(".joblib", "_meta.json")
            if Path(meta_path).exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                    self.feature_names = meta.get("feature_names", self.FEATURE_NAMES)

            # Initialize SHAP TreeExplainer
            try:
                import shap
                self.explainer = shap.TreeExplainer(self.model)
                logger.info("SHAP TreeExplainer initialized successfully.")
            except ImportError:
                logger.warning("SHAP not installed. Explanations will be limited.")
            except Exception as e:
                logger.warning(f"SHAP initialization failed: {e}")

            self.is_available = True
            logger.info(f"Risk model loaded from {model_path}")

        except ImportError:
            logger.warning("joblib not installed. Risk prediction unavailable.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    def predict_and_explain(
        self,
        features: dict[str, float],
        generate_plot: bool = False,
        plot_dir: str = "data/shap_plots",
    ) -> RiskPrediction:
        """Predict risk and generate SHAP explanation.

        Args:
            features: Dictionary of feature name -> value.
            generate_plot: Whether to generate a waterfall plot PNG.
            plot_dir: Directory to save the waterfall plot.

        Returns:
            RiskPrediction with score, level, top factors, and SHAP values.
        """
        import numpy as np

        if not self.is_available or self.model is None:
            return RiskPrediction(
                risk_score=0.0,
                risk_level="unknown",
                prediction=0,
                top_factors=[{"feature": "model_unavailable", "value": 0,
                             "impact": 0, "direction": "N/A"}],
            )

        # Build feature vector in correct order
        feature_vector = np.array([
            features.get(name, 0.0) for name in self.feature_names
        ]).reshape(1, -1)

        # Predict
        risk_prob = float(self.model.predict_proba(feature_vector)[0, 1])
        prediction = int(risk_prob >= 0.5)

        result = RiskPrediction(
            risk_score=round(risk_prob, 4),
            risk_level=_risk_level(risk_prob),
            prediction=prediction,
        )

        # SHAP explanation
        if self.explainer is not None:
            try:
                shap_values = self.explainer.shap_values(feature_vector)

                # Handle different SHAP output formats
                if isinstance(shap_values, list):
                    # Binary classification: [class_0_shap, class_1_shap]
                    sv = shap_values[1][0]  # Class 1 (risky)
                else:
                    sv = shap_values[0]

                result.shap_values = [round(float(v), 4) for v in sv]
                result.shap_base_value = round(
                    float(self.explainer.expected_value[1])
                    if isinstance(self.explainer.expected_value, (list, np.ndarray))
                    else float(self.explainer.expected_value),
                    4,
                )

                # Top contributing factors
                impacts = list(zip(self.feature_names, sv, feature_vector[0]))
                impacts.sort(key=lambda x: abs(x[1]), reverse=True)

                result.top_factors = [
                    {
                        "feature": name,
                        "value": round(float(val), 2),
                        "impact": round(float(shap_val), 4),
                        "direction": "↑ increases risk" if shap_val > 0 else "↓ decreases risk",
                    }
                    for name, shap_val, val in impacts[:8]
                ]

                # Generate waterfall plot if requested
                if generate_plot:
                    result.waterfall_plot_path = self._generate_waterfall(
                        feature_vector, plot_dir
                    )

            except Exception as e:
                logger.warning(f"SHAP explanation failed: {e}")
                result.top_factors = self._fallback_importance(feature_vector)
        else:
            result.top_factors = self._fallback_importance(feature_vector)

        return result

    def _fallback_importance(self, feature_vector) -> list[dict]:
        """Use XGBoost built-in feature importance when SHAP is unavailable."""
        if self.model is None:
            return []

        importances = self.model.feature_importances_
        pairs = sorted(
            zip(self.feature_names, importances, feature_vector[0]),
            key=lambda x: x[1], reverse=True,
        )

        return [
            {
                "feature": name,
                "value": round(float(val), 2),
                "impact": round(float(imp), 4),
                "direction": "importance (SHAP unavailable)",
            }
            for name, imp, val in pairs[:8]
        ]

    def _generate_waterfall(self, feature_vector, plot_dir: str) -> str | None:
        """Generate and save a SHAP waterfall plot."""
        try:
            import shap
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            os.makedirs(plot_dir, exist_ok=True)

            shap_explanation = self.explainer(feature_vector)

            fig, ax = plt.subplots(figsize=(10, 6))
            shap.plots.waterfall(shap_explanation[0], show=False)
            plt.title("FlagGuard Risk Prediction — SHAP Waterfall", fontsize=14)
            plt.tight_layout()

            plot_path = os.path.join(plot_dir, "shap_waterfall.png")
            plt.savefig(plot_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"SHAP waterfall plot saved to {plot_path}")
            return plot_path

        except Exception as e:
            logger.warning(f"Failed to generate waterfall plot: {e}")
            return None

    def get_model_info(self) -> dict:
        """Return model metadata for the API."""
        return {
            "model_type": "XGBClassifier",
            "features": self.feature_names,
            "num_features": len(self.feature_names),
            "is_available": self.is_available,
            "has_shap": self.explainer is not None,
        }
