#!/usr/bin/env python3
"""
scripts/train_models.py

Trains, cross-validates, benchmarks, and serializes all Phase 3 Predictive Intelligence models:
1. Stage Mean Baseline
2. Stage Median Baseline
3. Ridge Regression (Linear)
4. Random Forest Regressor
5. XGBoost Regressor
+ Distribution-Shift Detector (Domain Boundaries + Mahalanobis Distance)

Exports comprehensive CSV result files (compatible with Excel & GitHub):
- datasets/model_evaluation_results.csv
- datasets/model_predictions_comparison.csv
- datasets/distribution_shift_test_results.csv
(Also saved inside models/)
"""

import csv
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.prediction.predictor import CloudPilotPredictor

MODEL_DISPLAY_NAMES = {
    "stage_mean": "Stage Mean Baseline",
    "stage_median": "Stage Median Baseline",
    "ridge_regression": "Ridge Regression (Linear)",
    "random_forest": "Random Forest Regressor",
    "xgboost": "XGBoost Regressor",
}

MODEL_TIERS = {
    "stage_mean": "1_Statistical_Baseline",
    "stage_median": "1_Statistical_Baseline",
    "ridge_regression": "2_Linear_Regression",
    "random_forest": "3_Ensemble_Bagging_ML",
    "xgboost": "3_Ensemble_Boosting_ML",
}

TARGET_UNITS = {
    "runtime_seconds": "s",
    "actual_cpu": "cores",
    "actual_memory_mb": "MB",
}


def print_target_leaderboard(target_name: str, target_info: dict):
    unit = TARGET_UNITS.get(target_name, "")
    best_model = target_info["best_model"]
    models_dict = target_info["models"]

    print(f"\n{'=' * 82}")
    print(f"Target: {target_name} (5-Fold Cross-Validation Benchmark)")
    print(f"{'=' * 82}")
    header = f"{'Model':<28} | {'MAE (' + unit + ')':>12} | {'RMSE (' + unit + ')':>12} | {'MAPE (%)':>10} | {'R2 Score':>9} | {'Status':<8}"
    print(header)
    print("-" * 82)

    for m_key in ["stage_mean", "stage_median", "ridge_regression", "random_forest", "xgboost"]:
        if m_key not in models_dict:
            continue
        m = models_dict[m_key]
        disp = MODEL_DISPLAY_NAMES.get(m_key, m_key)
        status = "* BEST" if m_key == best_model else ""
        print(
            f"{disp:<28} | {m['mae']:>12.4f} | {m['rmse']:>12.4f} | {m['mape_pct']:>9.2f}% | {m['r2']:>9.4f} | {status:<8}"
        )


def export_evaluation_csv(summary: dict, out_path: Path):
    """Save 5-Fold Cross-Validation metrics for all 15 trained models to CSV."""
    fieldnames = [
        "target",
        "unit",
        "model_key",
        "model_name",
        "model_tier",
        "cv_folds",
        "dataset_rows",
        "mae",
        "rmse",
        "mape_pct",
        "r2_score",
        "is_best",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for target_name, target_info in summary["targets"].items():
            best_key = target_info["best_model"]
            unit = TARGET_UNITS.get(target_name, "")
            for m_key in ["stage_mean", "stage_median", "ridge_regression", "random_forest", "xgboost"]:
                if m_key not in target_info["models"]:
                    continue
                metrics = target_info["models"][m_key]
                writer.writerow(
                    {
                        "target": target_name,
                        "unit": unit,
                        "model_key": m_key,
                        "model_name": MODEL_DISPLAY_NAMES.get(m_key, m_key),
                        "model_tier": MODEL_TIERS.get(m_key, "ML"),
                        "cv_folds": summary["cv_folds"],
                        "dataset_rows": summary["dataset_rows"],
                        "mae": metrics["mae"],
                        "rmse": metrics["rmse"],
                        "mape_pct": metrics["mape_pct"],
                        "r2_score": metrics["r2"],
                        "is_best": m_key == best_key,
                    }
                )


def export_predictions_comparison_csv(predictor: CloudPilotPredictor, out_path: Path):
    """Save row-by-row actual vs predicted comparison across all 90 genomic runs to CSV."""
    X, y_dict, raw_rows = predictor.pipeline.prepare_training_data()

    rt_mean_preds = predictor.runtime_predictor.predict(X, model_name="stage_mean")
    rt_ridge_preds = predictor.runtime_predictor.predict(X, model_name="ridge_regression")
    rt_rf_preds = predictor.runtime_predictor.predict(X, model_name="random_forest")
    rt_xgb_preds = predictor.runtime_predictor.predict(X, model_name="xgboost")

    cpu_rf_preds = predictor.resource_predictor.cpu_model.predict(X, model_name="random_forest")
    cpu_xgb_preds = predictor.resource_predictor.cpu_model.predict(X, model_name="xgboost")

    mem_rf_preds = predictor.resource_predictor.memory_model.predict(X, model_name="random_forest")
    mem_xgb_preds = predictor.resource_predictor.memory_model.predict(X, model_name="xgboost")

    fieldnames = [
        "workflow_id",
        "stage_id",
        "stage_type",
        "workload_id",
        "region_size",
        "variant_count",
        "sample_count",
        "dataset_size_mb",
        "requested_cpu",
        "requested_memory_mb",
        "worker_count",
        "actual_runtime_s",
        "pred_runtime_mean_s",
        "pred_runtime_ridge_s",
        "pred_runtime_rf_s",
        "pred_runtime_xgb_s",
        "runtime_error_rf_s",
        "actual_cpu_cores",
        "pred_cpu_rf_cores",
        "pred_cpu_xgb_cores",
        "actual_memory_mb",
        "pred_memory_rf_mb",
        "pred_memory_xgb_mb",
        "recommended_workers",
        "confidence_pct",
        "distribution_shift",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(raw_rows):
            stage_pred = predictor.predict_stage(row)
            act_rt = float(row["runtime_seconds"])
            rf_rt = round(float(rt_rf_preds[i]), 3)

            writer.writerow(
                {
                    "workflow_id": row["workflow_id"],
                    "stage_id": row["stage_id"],
                    "stage_type": row["stage_type"],
                    "workload_id": row["workload_id"],
                    "region_size": int(row["region_size"]),
                    "variant_count": int(row["variant_count"]),
                    "sample_count": int(row["sample_count"]),
                    "dataset_size_mb": float(row["dataset_size_mb"]),
                    "requested_cpu": row["requested_cpu"],
                    "requested_memory_mb": float(row["requested_memory_mb"]),
                    "worker_count": int(row["worker_count"]),
                    "actual_runtime_s": round(act_rt, 3),
                    "pred_runtime_mean_s": round(float(rt_mean_preds[i]), 3),
                    "pred_runtime_ridge_s": round(float(rt_ridge_preds[i]), 3),
                    "pred_runtime_rf_s": rf_rt,
                    "pred_runtime_xgb_s": round(float(rt_xgb_preds[i]), 3),
                    "runtime_error_rf_s": round(abs(act_rt - rf_rt), 3),
                    "actual_cpu_cores": round(float(row["actual_cpu"]), 3),
                    "pred_cpu_rf_cores": round(float(cpu_rf_preds[i]), 3),
                    "pred_cpu_xgb_cores": round(float(cpu_xgb_preds[i]), 3),
                    "actual_memory_mb": round(float(row["actual_memory_mb"]), 2),
                    "pred_memory_rf_mb": round(float(mem_rf_preds[i]), 2),
                    "pred_memory_xgb_mb": round(float(mem_xgb_preds[i]), 2),
                    "recommended_workers": stage_pred["recommended_worker_count"],
                    "confidence_pct": stage_pred["confidence_pct"],
                    "distribution_shift": stage_pred["distribution_shift"],
                }
            )


def export_shift_scenarios_csv(predictor: CloudPilotPredictor, out_path: Path):
    """Save distribution-shift test scenarios (NORMAL, WARNING, SHIFTED) to CSV."""
    scenarios = [
        (
            "In-Distribution Small (100kb, 100 samples)",
            {
                "stage_id": "vcf_stats_chr22_small_100s",
                "stage_type": "vcf_stats",
                "workload_id": "chr22_small_100s",
                "requested_cpu": "500m",
                "requested_memory": "256Mi",
                "worker_count": 1,
            },
        ),
        (
            "In-Distribution Medium (1Mb, 500 samples)",
            {
                "stage_id": "variant_processing_chr22_medium_500s",
                "stage_type": "variant_processing",
                "workload_id": "chr22_medium_500s",
                "requested_cpu": "1000m",
                "requested_memory": "512Mi",
                "worker_count": 2,
            },
        ),
        (
            "In-Distribution Large (4Mb, 2504 samples)",
            {
                "stage_id": "analysis_chr22_large_full",
                "stage_type": "analysis",
                "workload_id": "chr22_large_full",
                "requested_cpu": "2000m",
                "requested_memory": "1Gi",
                "worker_count": 4,
            },
        ),
        (
            "Near-Boundary Warning (5.6Mb Region, 130k Variants)",
            {
                "stage_id": "filtering_boundary_warn",
                "stage_type": "filtering",
                "workload_id": "chr22_extended_region",
                "region_size": 5600000,
                "variant_count": 130000,
                "sample_count": 2504,
                "dataset_size_mb": 22.5,
                "requested_cpu": "1000m",
                "requested_memory": "1Gi",
                "worker_count": 2,
            },
        ),
        (
            "Out-of-Distribution Shift (100 GB Cohort / 1.5M Variants)",
            {
                "stage_id": "alignment_wgs_100gb",
                "stage_type": "variant_processing",
                "workload_id": "wgs_cohort_100gb",
                "region_size": 50000000,
                "variant_count": 1500000,
                "sample_count": 5000,
                "dataset_size_mb": 102400.0,
                "requested_cpu": "2000m",
                "requested_memory": "2Gi",
                "worker_count": 4,
            },
        ),
    ]

    fieldnames = [
        "scenario",
        "stage_id",
        "stage_type",
        "workload_id",
        "predicted_runtime_s",
        "expected_range_low_s",
        "expected_range_high_s",
        "predicted_cpu_cores",
        "predicted_memory_mb",
        "recommended_workers",
        "confidence_pct",
        "distribution_shift",
        "mahalanobis_distance",
        "fallback_recommended",
        "shift_reasons",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for label, inp in scenarios:
            pred = predictor.predict_stage(inp)
            writer.writerow(
                {
                    "scenario": label,
                    "stage_id": pred["stage_id"],
                    "stage_type": pred["stage_type"],
                    "workload_id": pred["workload_id"],
                    "predicted_runtime_s": pred["predicted_runtime_seconds"],
                    "expected_range_low_s": pred["expected_runtime_range"][0],
                    "expected_range_high_s": pred["expected_runtime_range"][1],
                    "predicted_cpu_cores": pred["predicted_actual_cpu"],
                    "predicted_memory_mb": pred["predicted_actual_memory_mb"],
                    "recommended_workers": pred["recommended_worker_count"],
                    "confidence_pct": pred["confidence_pct"],
                    "distribution_shift": pred["distribution_shift"],
                    "mahalanobis_distance": pred["shift_details"]["mahalanobis_distance"],
                    "fallback_recommended": pred["fallback_recommended"],
                    "shift_reasons": "; ".join(pred["shift_details"]["reasons"]) or "Within training distribution",
                }
            )


def main():
    print("CloudPilot Phase 3 - Predictive Intelligence Layer Training & Evaluation")
    predictor = CloudPilotPredictor()
    summary = predictor.train(n_splits=5)
    saved_dir = predictor.save_models()

    print(f"\nLoaded clean genomic dataset: {summary['dataset_rows']} rows")
    print(f"Cross-Validation Folds: {summary['cv_folds']}")

    for target_name, target_info in summary["targets"].items():
        print_target_leaderboard(target_name, target_info)

    # Export CSV result files to datasets/ and models/
    datasets_dir = ROOT_DIR / "datasets"
    eval_csv = datasets_dir / "model_evaluation_results.csv"
    preds_csv = datasets_dir / "model_predictions_comparison.csv"
    shift_csv = datasets_dir / "distribution_shift_test_results.csv"

    export_evaluation_csv(summary, eval_csv)
    export_predictions_comparison_csv(predictor, preds_csv)
    export_shift_scenarios_csv(predictor, shift_csv)

    shutil.copy2(eval_csv, saved_dir / eval_csv.name)
    shutil.copy2(preds_csv, saved_dir / preds_csv.name)
    shutil.copy2(shift_csv, saved_dir / shift_csv.name)

    print(f"\n{'=' * 82}")
    print("Exported Model Testing & Evaluation CSV Files:")
    print(f"  1. {eval_csv.relative_to(ROOT_DIR)}")
    print(f"  2. {preds_csv.relative_to(ROOT_DIR)}")
    print(f"  3. {shift_csv.relative_to(ROOT_DIR)}")
    print(f"  (Copies also stored in {saved_dir.relative_to(ROOT_DIR)}/)")
    print(f"{'=' * 82}")


if __name__ == "__main__":
    main()
