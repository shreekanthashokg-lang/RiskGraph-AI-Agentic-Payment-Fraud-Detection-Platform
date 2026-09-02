from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV

try:
    from sklearn.frozen import FrozenEstimator
    HAS_FROZEN_ESTIMATOR = True
except ImportError:
    HAS_FROZEN_ESTIMATOR = False
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.feature_engineering import TARGET_COL, to_model_matrix
from dataset_adapter import load_and_adapt

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


def _try_plots(y_test, y_prob, feature_names, importances, out_dir: Path):
    # plotting code unchanged...
    ...


def evaluate(y_true, y_prob, threshold: float) -> dict:
    # evaluation code unchanged...
    ...


def pick_threshold(y_true, y_prob) -> float:
    # threshold selection code unchanged...
    ...


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=str, default="data/sample/transactions_synthetic.csv")
    ap.add_argument("--out-dir", type=str, default="ml/artifacts")
    ap.add_argument("--reports-dir", type=str, default="reports")
    ap.add_argument("--processed-dir", type=str, default="data/processed")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    processed_dir = Path(args.processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Loading dataset: {args.data} ===")
    df, adapt_report = load_and_adapt(args.data)
    # dataset reporting code unchanged...

    X = to_model_matrix(df)
    y = df[TARGET_COL].astype(int).values
    feature_names = list(X.columns)

    processed_path = processed_dir / (Path(args.data).stem + "_processed.csv")
    df.to_csv(processed_path, index=False)

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, random_state=args.seed, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=args.seed, stratify=y_temp
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    _X_test_s = scaler.transform(X_test)  # renamed to avoid unused variable warning

    # --- Baseline: Logistic Regression ---
    baseline = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=args.seed)
    baseline.fit(X_train_s, y_train)
    baseline_val_prob = baseline.predict_proba(X_val_s)[:, 1]
    baseline_metrics = evaluate(y_val, baseline_val_prob, 0.5)

    # --- Production candidate: XGBoost (falls back to RandomForest) ---
    # training code unchanged...

    # rest of pipeline unchanged...
    ...


if __name__ == "__main__":
    main()
