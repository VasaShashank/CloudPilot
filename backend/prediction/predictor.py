import json
from pathlib import Path
from typing import Any, Dict, Optional
import joblib
import numpy as np

from backend.models.workflow import StageDefinition, WorkflowDefinition
from backend.prediction.drift import DistributionShiftDetector
from backend.prediction.feature_pipeline import (
    DEFAULT_GENOMIC_DATASET_PATH,
    FeatureMatrix,
    FeaturePipeline,
)
from backend.prediction.resource_model import ResourcePredictor
from backend.prediction.runtime_model import RuntimePredictor
from backend.workflow.dag import WorkflowDAG

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class CloudPilotPredictor:
    """
    Unified Phase 3 Predictive Intelligence Engine for CloudPilot.
    Combines:
    - Feature extraction & encoding
    - Runtime prediction (Baseline -> Ridge -> Random Forest / XGBoost)
    - Resource prediction (CPU, Memory, Recommended Worker Count)
    - Ensemble variance confidence scoring
    - Distribution-shift detection (Domain boundaries + Mahalanobis distance)
    """

    def __init__(
        self,
        dataset_path: Path = DEFAULT_GENOMIC_DATASET_PATH,
        model_dir: Path = DEFAULT_MODEL_DIR,
        confidence_fallback_threshold: float = 0.60,
    ):
        self.dataset_path = dataset_path
        self.model_dir = model_dir
        self.confidence_fallback_threshold = confidence_fallback_threshold

        self.pipeline = FeaturePipeline(dataset_path=dataset_path)
        self.runtime_predictor = RuntimePredictor()
        self.resource_predictor = ResourcePredictor()
        self.shift_detector = DistributionShiftDetector()
        self.evaluation_summary_: Dict[str, Any] = {}
        self.is_trained_: bool = False

    def train(self, filepath: Optional[Path] = None, n_splits: int = 5) -> Dict[str, Any]:
        """Train all models and evaluate 5-fold cross-validation accuracy across all 5 model tiers."""
        X, y_dict, raw_rows = self.pipeline.prepare_training_data(filepath)

        self.shift_detector.fit(X)
        rt_metrics = self.runtime_predictor.fit_and_evaluate(
            X, y_dict["runtime_seconds"], n_splits=n_splits
        )
        res_metrics = self.resource_predictor.fit_and_evaluate(
            X,
            y_cpu=y_dict["actual_cpu"],
            y_memory=y_dict["actual_memory_mb"],
            n_splits=n_splits,
        )

        self.evaluation_summary_ = {
            "dataset_rows": len(raw_rows),
            "cv_folds": n_splits,
            "targets": {
                "runtime_seconds": {
                    "untuned_best_model": self.runtime_predictor.untuned_best_model_name_,
                    "best_model": self.runtime_predictor.best_model_name_,
                    "best_params": self.runtime_predictor.best_params_,
                    "hyperparameter_optimization": self.runtime_predictor.hpo_summary_,
                    "models": rt_metrics,
                },
                "actual_cpu": {
                    "untuned_best_model": self.resource_predictor.cpu_model.untuned_best_model_name_,
                    "best_model": self.resource_predictor.cpu_model.best_model_name_,
                    "best_params": self.resource_predictor.cpu_model.best_params_,
                    "hyperparameter_optimization": self.resource_predictor.cpu_model.hpo_summary_,
                    "models": res_metrics["actual_cpu"],
                },
                "actual_memory_mb": {
                    "untuned_best_model": self.resource_predictor.memory_model.untuned_best_model_name_,
                    "best_model": self.resource_predictor.memory_model.best_model_name_,
                    "best_params": self.resource_predictor.memory_model.best_params_,
                    "hyperparameter_optimization": self.resource_predictor.memory_model.hpo_summary_,
                    "models": res_metrics["actual_memory_mb"],
                },
            },
        }
        self.is_trained_ = True
        return self.evaluation_summary_

    def save_models(self, model_dir: Optional[Path] = None) -> Path:
        """Persist trained models and evaluation metrics to disk."""
        if not self.is_trained_:
            raise RuntimeError("Cannot save untrained CloudPilotPredictor.")

        target_dir = model_dir or self.model_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / "runtime").mkdir(parents=True, exist_ok=True)
        (target_dir / "cpu").mkdir(parents=True, exist_ok=True)
        (target_dir / "memory").mkdir(parents=True, exist_ok=True)

        joblib.dump(self.runtime_predictor, target_dir / "runtime" / "model.joblib")
        joblib.dump(self.resource_predictor.cpu_model, target_dir / "cpu" / "model.joblib")
        joblib.dump(self.resource_predictor.memory_model, target_dir / "memory" / "model.joblib")
        joblib.dump(self.resource_predictor, target_dir / "resource_predictor.joblib")
        joblib.dump(self.shift_detector, target_dir / "shift_detector.joblib")

        with open(target_dir / "evaluation_summary.json", "w", encoding="utf-8") as f:
            json.dump(self.evaluation_summary_, f, indent=2)

        return target_dir

    def load_models(self, model_dir: Optional[Path] = None) -> "CloudPilotPredictor":
        """Load serialized models from disk (or train automatically if not found)."""
        target_dir = model_dir or self.model_dir
        rt_path = target_dir / "runtime" / "model.joblib"
        res_path = target_dir / "resource_predictor.joblib"
        shift_path = target_dir / "shift_detector.joblib"
        summary_path = target_dir / "evaluation_summary.json"

        if rt_path.exists() and res_path.exists() and shift_path.exists():
            self.runtime_predictor = joblib.load(rt_path)
            self.resource_predictor = joblib.load(res_path)
            self.shift_detector = joblib.load(shift_path)
            if summary_path.exists():
                with open(summary_path, "r", encoding="utf-8") as f:
                    self.evaluation_summary_ = json.load(f)
            self.is_trained_ = True
        else:
            self.train()
            self.save_models(target_dir)
        return self

    def predict_stage(
        self,
        stage_input: Dict[str, Any],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Predict runtime, CPU, memory, recommended workers, confidence, and distribution shift
        for a single workflow stage dictionary.
        """
        if not self.is_trained_:
            self.load_models()

        feat_dict = self.pipeline.extract_single_features(stage_input)
        X_row = FeatureMatrix(
            np.array([[feat_dict[c] for c in self.pipeline.feature_names]], dtype=float),
            self.pipeline.feature_names,
        )

        # 1. Distribution shift detection
        raw_stage_type = stage_input.get("stage_type", stage_input.get("type", "vcf_stats"))
        shift_info = self.shift_detector.evaluate_single(feat_dict, raw_stage_type=raw_stage_type)
        shift_penalty = shift_info["confidence_penalty"]

        # 2. Runtime prediction + confidence
        rt_info = self.runtime_predictor.predict_with_confidence(
            X_row, shift_penalty=shift_penalty, model_name=model_name
        )

        # 3. Predict runtime across candidate worker counts (1, 2, 4) for SLA scheduling
        worker_scaling: Dict[int, float] = {}
        for w in (1, 2, 4):
            w_input = dict(stage_input)
            w_input["worker_count"] = w
            curr_cpu = feat_dict["requested_cpu_cores"]
            w_input["requested_cpu_cores"] = max(curr_cpu, w * 0.5)
            w_feat = self.pipeline.extract_single_features(w_input)
            w_mat = FeatureMatrix(
                np.array([[w_feat[c] for c in self.pipeline.feature_names]], dtype=float),
                self.pipeline.feature_names,
            )
            w_rt = float(self.runtime_predictor.predict(w_mat, model_name=model_name)[0])
            worker_scaling[w] = round(w_rt, 3)

        # Enforce physical monotonic non-increasing runtime as workers increase
        worker_scaling[2] = round(min(worker_scaling[1], worker_scaling[2]), 3)
        worker_scaling[4] = round(min(worker_scaling[2], worker_scaling[4]), 3)

        # 4. Resource prediction (CPU, Memory, Recommended Worker Count)
        res_info = self.resource_predictor.predict_resources(
            X_row,
            feature_dict=feat_dict,
            shift_penalty=shift_penalty,
            predicted_runtime=worker_scaling[1],
            model_name=model_name,
        )

        # 5. Aggregate overall confidence
        overall_conf = round(
            0.50 * rt_info["confidence"]
            + 0.25 * res_info["cpu_confidence"]
            + 0.25 * res_info["memory_confidence"],
            4,
        )
        overall_conf_pct = round(overall_conf * 100.0, 1)

        fallback_recommended = bool(
            shift_info["fallback_recommended"] or overall_conf < self.confidence_fallback_threshold
        )

        return {
            "stage_id": str(stage_input.get("stage_id", stage_input.get("id", "unknown_stage"))),
            "stage_type": str(raw_stage_type),
            "workload_id": str(stage_input.get("workload_id", "custom")),
            "predicted_runtime_seconds": rt_info["predicted_runtime_seconds"],
            "expected_runtime_range": list(rt_info["expected_runtime_range"]),
            "predicted_actual_cpu": res_info["predicted_actual_cpu"],
            "expected_cpu_range": list(res_info["expected_cpu_range"]),
            "predicted_actual_memory_mb": res_info["predicted_actual_memory_mb"],
            "expected_memory_range": list(res_info["expected_memory_range"]),
            "recommended_worker_count": res_info["recommended_worker_count"],
            "worker_scaling_predictions": worker_scaling,
            "confidence": overall_conf,
            "confidence_pct": overall_conf_pct,
            "distribution_shift": shift_info["status"],
            "shift_details": shift_info,
            "fallback_recommended": fallback_recommended,
            "models_used": {
                "runtime": rt_info["model_used"],
                "cpu": res_info["cpu_model_used"],
                "memory": res_info["memory_model_used"],
            },
        }

    def predict_from_stage_definition(
        self,
        stage_def: StageDefinition,
        workload_metadata: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Predict requirements directly from a Pydantic StageDefinition."""
        env = stage_def.env or {}
        meta = dict(workload_metadata or {})
        stage_input: Dict[str, Any] = {
            "stage_id": stage_def.id,
            "stage_type": stage_def.type,
            "requested_cpu": stage_def.cpu or "1000m",
            "requested_memory": stage_def.memory or "512Mi",
            "worker_count": int(env.get("THREADS", meta.get("worker_count", 1))),
            "workload_id": env.get("WORKLOAD_ID", meta.get("workload_id")),
            "chunk_size": env.get("CHUNK_SIZE", meta.get("chunk_size", "small")),
        }
        for k in ("region_size", "variant_count", "sample_count", "dataset_size_mb", "chromosome"):
            if k in meta:
                stage_input[k] = meta[k]
        return self.predict_stage(stage_input, model_name=model_name)

    def predict_workflow(
        self,
        workflow_def: WorkflowDefinition,
        workload_metadata: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Predict runtime, resources, confidence, and shift for an entire workflow DAG.
        Calculates critical-path runtime across parallel branches.
        """
        if not self.is_trained_:
            self.load_models()

        dag = WorkflowDAG(workflow_def)
        stage_preds: Dict[str, Dict[str, Any]] = {}
        for stage in workflow_def.stages:
            stage_preds[stage.id] = self.predict_from_stage_definition(
                stage, workload_metadata=workload_metadata, model_name=model_name
            )

        earliest_finish: Dict[str, float] = {}
        for stage_id in dag.topological_order():
            deps = dag.get_dependencies(stage_id)
            dep_finish = max((earliest_finish[d] for d in deps), default=0.0)
            earliest_finish[stage_id] = dep_finish + stage_preds[stage_id]["predicted_runtime_seconds"]

        critical_path_runtime = round(max(earliest_finish.values(), default=0.0), 3)
        sequential_runtime = round(
            sum(p["predicted_runtime_seconds"] for p in stage_preds.values()), 3
        )
        avg_confidence = round(
            sum(p["confidence"] for p in stage_preds.values()) / max(1, len(stage_preds)), 4
        )
        any_shifted = any(p["distribution_shift"] == "SHIFTED" for p in stage_preds.values())
        any_warning = any(p["distribution_shift"] == "WARNING" for p in stage_preds.values())
        overall_shift = "SHIFTED" if any_shifted else ("WARNING" if any_warning else "NORMAL")

        return {
            "workflow_name": workflow_def.name,
            "critical_path_runtime_seconds": critical_path_runtime,
            "total_sequential_runtime_seconds": sequential_runtime,
            "average_confidence": avg_confidence,
            "average_confidence_pct": round(avg_confidence * 100.0, 1),
            "workflow_distribution_shift": overall_shift,
            "fallback_recommended": any(p["fallback_recommended"] for p in stage_preds.values()),
            "stages": stage_preds,
        }
