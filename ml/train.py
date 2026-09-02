from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sklearn.linear_model import LogisticRegression
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


def evaluate(y_true, y_prob, threshold: float) -> dict:
    from sklearn.metrics import (
        confusion_matrix,
        precision_score,
        recall_score,
        f1_score,
        roc_auc_score,
        average_precision_score,
    )
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "threshold": threshold,
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_true, y_prob), 4),
        "pr_auc": round(average_precision_score(y_true, y_prob), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def pick_threshold(y_true, y_prob) -> float:
    from sklearn.metrics import precision_recall_curve
    import numpy as np

    prec, rec, thresh = precision_recall_curve(y_true, y_prob)
    thresh = np.append(thresh, 1.0)
    f1s = np.where((prec + rec) > 0, 2 * prec * rec / (prec + rec + 1e-9), 0)
    min_recall = 0.5
    eligible = rec >= min_recall
    if eligible.any():
        candidate_idx = np.where(eligible)[0]
        best = candidate_idx[np.argmax(f1s[candidate_idx])]
    else:
        best = int(np.argmax(f1s))
    return float(np.clip(thresh[best], 0.01, 0.99))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=str, default="data/sample/transactions_synthetic.csv")
    ap.add_argument("--out-dir", type=str, default="ml/artifacts")
    ap.add_argument("--processed-dir", type=str, default="data/processed")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    processed_dir = Path(args.processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Loading dataset: {args.data} ===")
    df, adapt_report = load_and_adapt(args.data)

    assert TARGET_COL in df.columns, f"Training data must contain '{TARGET_COL}'"

    X = to_model_matrix(df)
    y = df[TARGET_COL].astype(int).values

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
    _baseline_metrics = evaluate(y_val, baseline_val_prob, 0.5)  # renamed to avoid unused variable warning

    # --- Production candidate: XGBoost (falls back to RandomForest) ---
    if HAS_XGB:
        scale_pos_weight = (y_train == 0).sum() / max(1, (y_train == 1).sum())
        raw_model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric="aucpr",
            random_state=args.seed,
            n_jobs=-1,
        )
    else:
        from sklearn.ensemble import RandomForestClassifier
        raw_model = RandomForestClassifier(
            n_estimators=400, max_depth=10, class_weight="balanced_subsample",
            random_state=args.seed, n_jobs=-1,
        )

    raw_model.fit(X_train, y_train)

    from sklearn.calibration import CalibratedClassifierCV
    calibrated = CalibratedClassifierCV(raw_model, method="isotonic", cv="prefit")
    calibrated.fit(X_val, y_val)

    val_prob = calibrated.predict_proba(X_val)[:, 1]
    threshold = pick_threshold(y_val, val_prob)

    test_prob = calibrated.predict_proba(X_test)[:, 1]
    test_metrics = evaluate(y_test, test_prob, threshold)

    print("\n=== Selected model & test metrics ===")
    print(test_metrics)


if __name__ == "__main__":
    main()
