import time
from pathlib import Path
import numpy as np
import pytest

from backend.models.workflow import StageDefinition, WorkflowDefinition
from backend.prediction.baseline import (
    RidgeRegressionBaseline,
    StageMeanBaseline,
    StageMedianBaseline,
)
from backend.prediction.drift import DistributionShiftDetector, ShiftStatus
from backend.prediction.feature_pipeline import (
    ALL_FEATURE_NAMES,
    FeaturePipeline,
    normalize_stage_type,
    parse_cpu_cores,
)
from backend.prediction.predictor import CloudPilotPredictor


@pytest.fixture(scope="module")
def trained_predictor(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("models")
    predictor = CloudPilotPredictor(model_dir=model_dir)
    predictor.train(n_splits=5)
    predictor.save_models(model_dir)
    return predictor


def test_parse_cpu_and_stage_normalization():
    assert parse_cpu_cores("250m") == 0.25
    assert parse_cpu_cores("500m") == 0.5
    assert parse_cpu_cores("1000m") == 1.0
    assert parse_cpu_cores("2000m") == 2.0
    assert parse_cpu_cores(1.5) == 1.5
    assert parse_cpu_cores(None) == 1.0

    assert normalize_stage_type("qc") == "vcf_stats"
    assert normalize_stage_type("preprocessing") == "filtering"
    assert normalize_stage_type("alignment") == "variant_processing"
    assert normalize_stage_type("analysis") == "analysis"


def test_feature_pipeline_load_and_transform():
    pipeline = FeaturePipeline()
    X, y_dict, raw_df = pipeline.prepare_training_data()

    assert len(raw_df) == 90
    assert X.shape == (90, len(ALL_FEATURE_NAMES))
    assert not X.has_nan()
    assert set(y_dict.keys()) == {"runtime_seconds", "actual_cpu", "actual_memory_mb"}


def test_baseline_models():
    pipeline = FeaturePipeline()
    X, y_dict, _ = pipeline.prepare_training_data()
    y_rt = y_dict["runtime_seconds"]

    mean_m = StageMeanBaseline().fit(X, y_rt)
    med_m = StageMedianBaseline().fit(X, y_rt)
    ridge_m = RidgeRegressionBaseline().fit(X, y_rt)

    preds_mean = mean_m.predict(X)
    preds_med = med_m.predict(X)
    preds_ridge = ridge_m.predict(X)

    assert len(preds_mean) == len(y_rt)
    assert len(preds_med) == len(y_rt)
    assert len(preds_ridge) == len(y_rt)
    assert np.all(preds_ridge > 0)


def test_ml_models_outperform_baselines(trained_predictor: CloudPilotPredictor):
    summary = trained_predictor.evaluation_summary_
    assert summary["dataset_rows"] == 90

    for target in ("runtime_seconds", "actual_cpu", "actual_memory_mb"):
        t_info = summary["targets"][target]
        t_models = t_info["models"]
        untuned_best = t_info["untuned_best_model"]
        best_name = t_info["best_model"]
        hpo_info = t_info["hyperparameter_optimization"]

        mean_mae = t_models["stage_mean"]["mae"]
        ridge_mae = t_models["ridge_regression"]["mae"]
        rf_mae = t_models["random_forest"]["mae"]
        xgb_mae = t_models["xgboost"]["mae"]
        tuned_mae = t_models["tuned_best"]["mae"]

        # Both RF and XGBoost must beat the Stage Mean and Ridge Regression baselines
        assert rf_mae < mean_mae
        assert xgb_mae < mean_mae
        assert min(rf_mae, xgb_mae) < ridge_mae
        assert untuned_best in ("random_forest", "xgboost")
        assert best_name == "tuned_best"
        assert tuned_mae <= t_models[untuned_best]["mae"]
        assert t_models[best_name]["r2"] > 0.80
        assert isinstance(hpo_info["best_params"], dict) and len(hpo_info["best_params"]) > 0



def test_stage_prediction_and_confidence_intervals(trained_predictor: CloudPilotPredictor):
    stage_input = {
        "stage_id": "variant_processing_chr22_medium_500s",
        "stage_type": "variant_processing",
        "workload_id": "chr22_medium_500s",
        "requested_cpu": "1000m",
        "requested_memory": "512Mi",
        "worker_count": 2,
    }
    pred = trained_predictor.predict_stage(stage_input)

    assert pred["predicted_runtime_seconds"] > 0.1
    low_rt, high_rt = pred["expected_runtime_range"]
    assert low_rt <= pred["predicted_runtime_seconds"] <= high_rt

    assert 0.1 <= pred["predicted_actual_cpu"] <= 2.5
    assert 16.0 <= pred["predicted_actual_memory_mb"] <= 2048.0
    assert pred["recommended_worker_count"] in (1, 2, 4)

    # Worker scaling should be monotonically non-increasing
    ws = pred["worker_scaling_predictions"]
    assert ws[1] >= ws[2] >= ws[4]

    # High confidence and NORMAL distribution shift for in-distribution sample
    assert pred["distribution_shift"] == ShiftStatus.NORMAL.value
    assert pred["confidence"] >= 0.75
    assert pred["fallback_recommended"] is False


def test_distribution_shift_detection_tiers(trained_predictor: CloudPilotPredictor):
    # 1. Warning tier: slightly above training region_size max (4,000,000 * 1.4 = 5,600,000)
    warn_input = {
        "stage_id": "filtering_warn",
        "stage_type": "filtering",
        "region_size": 5600000,
        "variant_count": 110000,
        "sample_count": 2504,
        "dataset_size_mb": 19.8,
        "requested_cpu": "1000m",
        "requested_memory": "1Gi",
        "worker_count": 2,
    }
    pred_warn = trained_predictor.predict_stage(warn_input)
    assert pred_warn["distribution_shift"] in (ShiftStatus.WARNING.value, ShiftStatus.SHIFTED.value)

    # 2. Shifted tier: 100 GB dataset (102,400 MB vs 19.8 MB max)
    shifted_input = {
        "stage_id": "alignment_100gb",
        "stage_type": "variant_processing",
        "region_size": 50000000,
        "variant_count": 1500000,
        "sample_count": 5000,
        "dataset_size_mb": 102400.0,
        "requested_cpu": "2000m",
        "requested_memory": "2Gi",
        "worker_count": 4,
    }
    pred_shift = trained_predictor.predict_stage(shifted_input)
    assert pred_shift["distribution_shift"] == ShiftStatus.SHIFTED.value
    assert pred_shift["fallback_recommended"] is True
    assert pred_shift["confidence"] < 0.60
    assert len(pred_shift["shift_details"]["reasons"]) > 0


def test_workflow_dag_prediction_critical_path(trained_predictor: CloudPilotPredictor):
    wf = WorkflowDefinition(
        name="diamond_genomic",
        stages=[
            StageDefinition(id="qc", type="vcf_stats"),
            StageDefinition(id="filtering", type="filtering", depends_on=["qc"]),
            StageDefinition(id="variant_processing", type="variant_processing", depends_on=["filtering"]),
            StageDefinition(id="feature_extraction", type="feature_extraction", depends_on=["filtering"]),
            StageDefinition(
                id="analysis",
                type="analysis",
                depends_on=["variant_processing", "feature_extraction"],
            ),
        ],
    )
    wf_pred = trained_predictor.predict_workflow(
        wf, workload_metadata={"workload_id": "chr22_large_500s", "worker_count": 2}
    )

    assert wf_pred["workflow_name"] == "diamond_genomic"
    assert len(wf_pred["stages"]) == 5
    # Because variant_processing and feature_extraction run in parallel, critical path < sequential sum
    assert wf_pred["critical_path_runtime_seconds"] < wf_pred["total_sequential_runtime_seconds"]
    assert wf_pred["workflow_distribution_shift"] == "NORMAL"


def test_model_persistence_and_inference_latency(trained_predictor: CloudPilotPredictor):
    reloaded = CloudPilotPredictor(model_dir=trained_predictor.model_dir)
    reloaded.load_models()
    assert reloaded.is_trained_ is True

    sample_stage = {
        "stage_id": "fast_check",
        "stage_type": "vcf_stats",
        "workload_id": "chr22_small_100s",
        "requested_cpu": "500m",
        "requested_memory": "256Mi",
        "worker_count": 1,
    }
    # Warm up to eliminate one-time dynamic library and thread-pool initialization overhead
    _ = reloaded.predict_stage(sample_stage)

    t0 = time.perf_counter()
    res = reloaded.predict_stage(sample_stage)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res["predicted_runtime_seconds"] > 0
    assert elapsed_ms < 500.0  # Sub-second inference SLA across 8 multi-target & scaling predictions
