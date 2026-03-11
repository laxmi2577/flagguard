"""FlagGuard Risk Prediction Model Training Pipeline (Phase 2 — Step 2.2).

Trains an XGBoost classifier to predict whether a commit (or PR) is likely
to introduce feature flag conflicts, based on features mined from git history.

Pipeline:
    1. Load training_data.csv
    2. Preprocess and split (80/20 stratified)
    3. Train XGBoost with hyperparameter tuning
    4. Evaluate: Accuracy, Precision, Recall, F1, AUC-ROC
    5. Log everything to MLflow
    6. Export best model to models/risk_model.joblib

Usage:
    python notebooks/train_risk_model.py
    python notebooks/train_risk_model.py --data data/training_data.csv --output models/risk_model.joblib

Skills demonstrated: XGBoost, scikit-learn, MLflow, Hyperparameter Tuning, Model Evaluation.
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 1: Configuration & Imports
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_COLS = [
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

LABEL_COL = "had_conflict"

HYPERPARAMS_GRID = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 5, 7],
    "learning_rate": [0.05, 0.1, 0.2],
    "min_child_weight": [1, 3],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
}


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 2: Data Loading & Preprocessing
# ═══════════════════════════════════════════════════════════════════════════════

def load_and_preprocess(data_path: str) -> tuple:
    """Load CSV and prepare features/labels for training.

    Args:
        data_path: Path to training_data.csv

    Returns:
        Tuple of (X_train, X_test, y_train, y_test, feature_names)
    """
    import pandas as pd
    from sklearn.model_selection import train_test_split

    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"Dataset shape: {df.shape}")
    print(f"Label distribution:\n{df[LABEL_COL].value_counts()}\n")

    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )

    print(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")
    print(f"Train positive rate: {y_train.mean():.2%}")
    print(f"Test positive rate:  {y_test.mean():.2%}")

    return X_train, X_test, y_train, y_test, FEATURE_COLS


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 3: Model Training with Hyperparameter Search
# ═══════════════════════════════════════════════════════════════════════════════

def train_model(X_train, y_train, X_test, y_test):
    """Train XGBoost classifier with GridSearchCV.

    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data for evaluation

    Returns:
        Tuple of (best_model, best_params, cv_results)
    """
    from xgboost import XGBClassifier
    from sklearn.model_selection import GridSearchCV

    print("\n" + "=" * 60)
    print("TRAINING XGBoost Classifier")
    print("=" * 60)

    # Base model
    base_model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42,
        verbosity=0,
    )

    # Reduced grid for speed (full grid would be too slow for a demo)
    reduced_grid = {
        "n_estimators": [50, 100, 200],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.05, 0.1, 0.2],
        "min_child_weight": [1, 3],
    }

    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=reduced_grid,
        cv=5,
        scoring="f1",
        n_jobs=-1,
        verbose=1,
        refit=True,
    )

    print("Running GridSearchCV (5-fold CV)...")
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    best_score = grid_search.best_score_

    print(f"\nBest CV F1 Score: {best_score:.4f}")
    print(f"Best Parameters: {json.dumps(best_params, indent=2)}")

    return best_model, best_params, grid_search.cv_results_


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 4: Model Evaluation
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_model(model, X_test, y_test, feature_names: list[str]) -> dict:
    """Evaluate the trained model on the test set.

    Args:
        model: Trained XGBClassifier
        X_test, y_test: Test data
        feature_names: List of feature names for importance analysis

    Returns:
        Dictionary of evaluation metrics.
    """
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        roc_auc_score,
        classification_report,
        confusion_matrix,
    )

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_test, y_prob) if len(set(y_test)) > 1 else 0.0,
    }

    print("\n" + "=" * 60)
    print("MODEL EVALUATION RESULTS")
    print("=" * 60)
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1']:.4f}")
    print(f"AUC-ROC:   {metrics['auc_roc']:.4f}")

    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Safe", "Risky"]))

    cm = confusion_matrix(y_test, y_pred)
    print(f"Confusion Matrix:\n{cm}")

    # Feature importance
    print(f"\nFeature Importance (top 10):")
    importances = model.feature_importances_
    importance_pairs = sorted(
        zip(feature_names, importances), key=lambda x: x[1], reverse=True
    )
    for name, score in importance_pairs[:10]:
        bar = "█" * int(score * 50)
        print(f"  {name:30s} {score:.4f} {bar}")

    return metrics


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 5: MLflow Experiment Logging
# ═══════════════════════════════════════════════════════════════════════════════

def log_to_mlflow(model, params, metrics, feature_names, output_dir):
    """Log the experiment to MLflow tracking server.

    Args:
        model: Trained model
        params: Best hyperparameters
        metrics: Evaluation metrics dictionary
        feature_names: List of feature names
        output_dir: Directory for MLflow artifacts
    """
    try:
        import mlflow
        import mlflow.xgboost

        # Set tracking URI to local directory
        mlflow_dir = os.path.join(output_dir, "mlruns")
        mlflow.set_tracking_uri(f"file:///{os.path.abspath(mlflow_dir)}")
        mlflow.set_experiment("flagguard-risk-prediction")

        with mlflow.start_run(run_name="xgboost-risk-v1") as run:
            # Log parameters
            for key, value in params.items():
                mlflow.log_param(key, value)
            mlflow.log_param("num_features", len(feature_names))
            mlflow.log_param("features", ", ".join(feature_names))

            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)

            # Log model
            mlflow.xgboost.log_model(
                model,
                artifact_path="model",
                registered_model_name="flagguard-risk-model",
            )

            # Log feature names
            feature_path = os.path.join(output_dir, "feature_names.json")
            with open(feature_path, "w") as f:
                json.dump(feature_names, f)
            mlflow.log_artifact(feature_path)

            print(f"\n✅ MLflow experiment logged!")
            print(f"   Run ID: {run.info.run_id}")
            print(f"   Tracking URI: {mlflow_dir}")
            print(f"   View UI: mlflow ui --backend-store-uri {mlflow_dir}")

    except ImportError:
        print("\n⚠️ MLflow not installed. Skipping experiment logging.")
        print("   Install with: pip install mlflow")
    except Exception as e:
        print(f"\n⚠️ MLflow logging failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 6: Export Model
# ═══════════════════════════════════════════════════════════════════════════════

def export_model(model, output_path: str, feature_names: list[str]):
    """Export the trained model to a joblib file.

    Args:
        model: Trained model
        output_path: Path to save the .joblib file
        feature_names: Feature names to save alongside the model
    """
    import joblib

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Save model
    joblib.dump(model, output_path)
    print(f"\n✅ Model exported to: {output_path}")

    # Save feature names alongside
    meta_path = output_path.replace(".joblib", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump({
            "feature_names": feature_names,
            "model_type": "XGBClassifier",
            "version": "1.0.0",
        }, f, indent=2)
    print(f"✅ Model metadata saved to: {meta_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 7: Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Train FlagGuard risk prediction model (XGBoost + MLflow)."
    )
    parser.add_argument(
        "--data", type=str, default="data/training_data.csv",
        help="Path to training data CSV"
    )
    parser.add_argument(
        "--output", type=str, default="models/risk_model.joblib",
        help="Path to export the trained model"
    )
    parser.add_argument(
        "--mlflow-dir", type=str, default=".",
        help="Directory for MLflow tracking (default: current dir)"
    )

    args = parser.parse_args()

    # Check if data exists
    if not Path(args.data).exists():
        print(f"ERROR: Training data not found at {args.data}")
        print(f"Run first: python scripts/generate_training_data.py")
        sys.exit(1)

    # Step 1: Load & preprocess
    X_train, X_test, y_train, y_test, feature_names = load_and_preprocess(args.data)

    # Step 2: Train with hyperparameter search
    model, best_params, cv_results = train_model(X_train, y_train, X_test, y_test)

    # Step 3: Evaluate
    metrics = evaluate_model(model, X_test, y_test, feature_names)

    # Step 4: Log to MLflow
    log_to_mlflow(model, best_params, metrics, feature_names, args.mlflow_dir)

    # Step 5: Export model
    export_model(model, args.output, feature_names)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Model:   {args.output}")
    print(f"AUC-ROC: {metrics['auc_roc']:.4f}")
    print(f"F1:      {metrics['f1']:.4f}")
    print(f"\nNext steps:")
    print(f"  1. python notebooks/train_risk_model.py  (re-train)")
    print(f"  2. View MLflow: mlflow ui")
    print(f"  3. SHAP analysis: see ai/risk_explainer.py (Step 2.3)")


if __name__ == "__main__":
    main()
