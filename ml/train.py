"""
RiskGraph AI - ML training pipeline
------------------------------------
Raw data -> validation -> feature engineering -> train/val/test split ->
baseline (Logistic Regression) -> production candidate (XGBoost, falls back
to RandomForest if xgboost isn't installed) -> probability calibration ->
evaluation -> artifacts (model.pkl, metrics.json, plots).

Run:
    python ml/train.py --data data/sample/transactions_synthetic.csv
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV

try:
    from sklearn.frozen import FrozenEstimator
    HAS_FROZEN_ESTIMATOR = True
except ImportError:
    HAS_FROZEN_ESTIMATOR = False
from sklearn.ensemble import RandomForestClassifier, IsolationForest
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
from app.services.feature_engineering import to_model_matrix, TARGET_COL  # noqa: E402
from dataset_adapter import load_and_adapt  # noqa: E402  (ml/ dir is on sys.path[0])

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


def _try_plots(y_test, y_prob, feature_names, importances, out_dir: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping PNG plots (metrics.json still produced).")
        return

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    plt.figure()
    plt.plot(fpr, tpr, label="ROC")
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend()
    plt.savefig(out_dir / "roc_curve.png", dpi=120, bbox_inches="tight")
    plt.close()

    prec, rec, _ = precision_recall_curve(y_test, y_prob)
    plt.figure()
    plt.plot(rec, prec)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.savefig(out_dir / "precision_recall_curve.png", dpi=120, bbox_inches="tight")
    plt.close()

    cm = confusion_matrix(y_test, (y_prob >= 0.5).astype(int))
    plt.figure()
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion Matrix (threshold=0.5)")
    plt.colorbar()
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center")
    plt.xticks([0, 1], ["Pred 0", "Pred 1"])
    plt.yticks([0, 1], ["True 0", "True 1"])
    plt.savefig(out_dir / "confusion_matrix.png", dpi=120, bbox_inches="tight")
    plt.close()

    if importances is not None:
        order = np.argsort(importances)[::-1][:15]
        plt.figure(figsize=(6, 5))
        plt.barh([feature_names[i] for i in order][::-1], importances[order][::-1])
        plt.title("Feature Importance (top 15)")
        plt.tight_layout()
        plt.savefig(out_dir / "feature_importance.png", dpi=120, bbox_inches="tight")
        plt.close()


def evaluate(y_true, y_prob, threshold: float) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "threshold": threshold,
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_true, y_prob), 4),
        "pr_auc": round(average_precision_score(y_true, y_prob), 4),
        "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "false_negative_rate": round(fn / (fn + tp), 4) if (fn + tp) else 0.0,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def pick_threshold(y_true, y_prob) -> float:
    """
    Choose the threshold that maximizes F1 on the validation set, subject to
    a minimum recall floor (fraud detection prefers not to miss too much
    fraud). This choice - and the reasoning - is persisted to metrics.json so
    it's auditable, per the "explain why the threshold was chosen" requirement.
    """
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
    print(f"Detected schema : {adapt_report['detected_schema']}")
    print(f"Raw shape       : {adapt_report['raw_rows']} rows x {adapt_report['raw_columns']} cols")
    if "engineered_columns_added" in adapt_report:
        print(f"Engineered cols : {adapt_report['engineered_columns_added']}")
        print(f"Defaulted to 0  : {adapt_report['columns_defaulted_zero_no_source_signal']} (no source signal in this dataset)")
        print(f"Not fabricated  : {adapt_report['columns_intentionally_not_fabricated']}")

    assert TARGET_COL in df.columns, f"Training data must contain '{TARGET_COL}'"

    missing_before = df.isna().sum()
    missing_report = {k: int(v) for k, v in missing_before.items() if v > 0}
    n_before_dropna = len(df)
    df = df.dropna(subset=[TARGET_COL])
    n_after_dropna = len(df)

    class_counts = df[TARGET_COL].value_counts().to_dict()
    class_counts = {str(k): int(v) for k, v in class_counts.items()}
    fraud_rate = float(df[TARGET_COL].mean())

    print(f"Rows after dropping missing target: {n_after_dropna} (dropped {n_before_dropna - n_after_dropna})")
    print(f"Missing values by column (non-zero only): {missing_report if missing_report else 'none'}")
    print(f"Class distribution ({TARGET_COL}): {class_counts}  (positive rate: {fraud_rate:.4%})")

    X = to_model_matrix(df)
    y = df[TARGET_COL].astype(int).values
    feature_names = list(X.columns)
    print(f"Detected target : '{TARGET_COL}'")
    print(f"Features used   ({len(feature_names)}): {feature_names}")

    # Persist the adapted/engineered dataset as a processed artifact.
    processed_path = processed_dir / (Path(args.data).stem + "_processed.csv")
    df.to_csv(processed_path, index=False)
    print(f"Processed dataset saved to: {processed_path}")

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, random_state=args.seed, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=args.seed, stratify=y_temp
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    # --- Baseline: Logistic Regression ---
    baseline = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=args.seed)
    baseline.fit(X_train_s, y_train)
    baseline_val_prob = baseline.predict_proba(X_val_s)[:, 1]
    baseline_metrics = evaluate(y_val, baseline_val_prob, 0.5)

    # --- Production candidate: XGBoost (falls back to RandomForest) ---
    t0 = time.time()
    if HAS_XGB:
        scale_pos_weight = (y_train == 0).sum() / max(1, (y_train == 1).sum())
        model_name = "xgboost"
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
        model_name = "random_forest_fallback"
        raw_model = RandomForestClassifier(
            n_estimators=400, max_depth=10, class_weight="balanced_subsample",
            random_state=args.seed, n_jobs=-1,
        )
        print("xgboost not installed in this environment - trained RandomForest fallback. "
              "Install xgboost and re-run for the production candidate.")

    raw_model.fit(X_train, y_train)
    train_latency_ms = (time.time() - t0) * 1000

    # Probability calibration (isotonic on validation fold, model kept frozen)
    if HAS_FROZEN_ESTIMATOR:
        calibrated = CalibratedClassifierCV(FrozenEstimator(raw_model), method="isotonic")
    else:  # older scikit-learn
        calibrated = CalibratedClassifierCV(raw_model, method="isotonic", cv="prefit")
    calibrated.fit(X_val, y_val)

    val_prob = calibrated.predict_proba(X_val)[:, 1]
    threshold = pick_threshold(y_val, val_prob)

    t1 = time.time()
    test_prob = calibrated.predict_proba(X_test)[:, 1]
    inference_latency_ms = ((time.time() - t1) / max(1, len(X_test))) * 1000

    test_metrics = evaluate(y_test, test_prob, threshold)

    importances = getattr(raw_model, "feature_importances_", None)

    metrics = {
        "dataset_path": str(args.data),
        "dataset_schema_detected": adapt_report["detected_schema"],
        "dataset_is_synthetic": "synthetic" in Path(args.data).stem.lower() or "synthetic" in adapt_report["detected_schema"].lower(),
        "raw_rows": adapt_report["raw_rows"],
        "raw_columns": adapt_report["raw_columns"],
        "rows_used_after_cleaning": n_after_dropna,
        "rows_dropped_missing_target": n_before_dropna - n_after_dropna,
        "missing_values_by_column": missing_report,
        "class_distribution": class_counts,
        "model_name": model_name,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        "fraud_rate_overall": round(float(y.mean()), 4),
        "baseline_logreg_val_metrics_at_0.5": baseline_metrics,
        "selected_threshold": threshold,
        "threshold_selection_rationale": (
            "Threshold chosen on the validation split to maximize F1 subject to a "
            "minimum recall floor of 0.5 (fraud detection prioritizes not missing fraud "
            "over avoiding every false positive). See precision_recall_curve.png."
        ),
        "test_metrics_at_selected_threshold": test_metrics,
        "train_latency_ms": round(train_latency_ms, 2),
        "inference_latency_ms_per_txn": round(inference_latency_ms, 4),
        "feature_names": feature_names,
        "model_artifact_path": str(out_dir / "model.pkl"),
    }

    print("\n=== Selected model & test metrics ===")
    print(f"Model: {model_name}")
    print(json.dumps(test_metrics, indent=2))

    _try_plots(y_test, test_prob, np.array(feature_names), importances, out_dir)

    # --- classification report + duplicate reports into reports/ per spec ---
    y_test_pred = (test_prob >= threshold).astype(int)
    clf_report_text = classification_report(y_test, y_test_pred, target_names=["legit", "fraud"], zero_division=0)
    (reports_dir / "classification_report.txt").write_text(clf_report_text)
    print("\n=== classification_report (test set, selected threshold) ===")
    print(clf_report_text)

    # --- Anomaly detector (unsupervised, trained on non-fraud only) ---
    iso = IsolationForest(n_estimators=200, contamination=0.03, random_state=args.seed)
    iso.fit(X_train[y_train == 0])

    model_version = f"{model_name}-{metrics['trained_at']}"
    joblib.dump(
        {
            "model": calibrated,
            "raw_model": raw_model,
            "scaler": scaler,
            "isolation_forest": iso,
            "feature_names": feature_names,
            "threshold": threshold,
            "model_version": model_version,
        },
        out_dir / "model.pkl",
    )
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    model_metadata = {
        "model_version": model_version,
        "model_name": model_name,
        "trained_at": metrics["trained_at"],
        "dataset_path": str(args.data),
        "dataset_is_synthetic": metrics["dataset_is_synthetic"],
        "rows_trained_on": n_after_dropna,
        "feature_names": feature_names,
        "selected_threshold": threshold,
        "test_metrics": test_metrics,
        "artifact_path": str((out_dir / "model.pkl").resolve()),
    }
    (out_dir / "model_metadata.json").write_text(json.dumps(model_metadata, indent=2))

    # Mirror the key reports into reports/ as well (metrics.json + plots),
    # alongside the classification_report.txt already written there.
    import shutil
    shutil.copy(out_dir / "metrics.json", reports_dir / "metrics.json")
    for png in ["confusion_matrix.png", "roc_curve.png", "precision_recall_curve.png", "feature_importance.png"]:
        src = out_dir / png
        if src.exists():
            shutil.copy(src, reports_dir / png)

    print(f"\nArtifacts written to {out_dir}/ (model.pkl, metrics.json, model_metadata.json, plots)")
    print(f"Reports written to {reports_dir}/ (metrics.json, classification_report.txt, plots)")
    print(f"Processed dataset written to {processed_path}")


if __name__ == "__main__":
    main()
