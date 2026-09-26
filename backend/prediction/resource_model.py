from typing import Any, Dict, Optional, Union
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

from backend.prediction.confidence import ConfidenceEstimator
from backend.prediction.feature_pipeline import FeatureMatrix
from backend.prediction.runtime_model import (
    build_candidate_models,
    compute_regression_metrics,
)


class SingleTargetResourceModel:
    """
    Trains and evaluates the 5-model progression for a single resource metric
    (either actual_cpu or actual_memory_mb).
    """

    def __init__(self, target_name: str, min_value: float = 0.1):
        self.target_name = target_name
        self.min_value = min_value
        self.models_: Dict[str, Any] = {}
        self.cv_metrics_: Dict[str, Dict[str, float]] = {}
        self.best_model_name_: str = "random_forest"
        self.confidence_estimator = ConfidenceEstimator(gamma=0.60, min_floor=min_value)
        self.is_fitted_: bool = False

    def fit_and_evaluate(
        self, X: FeatureMatrix, y: np.ndarray, n_splits: int = 5
    ) -> Dict[str, Dict[str, float]]:
        y_arr = np.asarray(y, dtype=float)
        candidates = build_candidate_models(min_clip=self.min_value)
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

        self.cv_metrics_ = {}
        self.models_ = {}

        for name, base_model in candidates.items():
            oof_preds = np.zeros_like(y_arr, dtype=float)
            for train_idx, val_idx in kf.split(X.to_numpy()):
                X_tr = X.slice_rows(train_idx)
                y_tr = y_arr[train_idx]
                X_va = X.slice_rows(val_idx)

                m = clone(base_model)
                if name in ("random_forest", "xgboost"):
                    m.fit(X_tr.to_numpy(dtype=float), y_tr)
                    preds = m.predict(X_va.to_numpy(dtype=float))
                else:
                    m.fit(X_tr, y_tr)
                    preds = m.predict(X_va)

                oof_preds[val_idx] = np.maximum(self.min_value, preds)

            self.cv_metrics_[name] = compute_regression_metrics(y_arr, oof_preds)

            fitted_model = clone(base_model)
            if name in ("random_forest", "xgboost"):
                fitted_model.fit(X.to_numpy(dtype=float), y_arr)
            else:
                fitted_model.fit(X, y_arr)
            self.models_[name] = fitted_model

        self.best_model_name_ = min(
            self.cv_metrics_.keys(), key=lambda k: self.cv_metrics_[k]["mae"]
        )
        self.is_fitted_ = True
        return self.cv_metrics_

    def predict(
        self,
        X: Union[FeatureMatrix, np.ndarray],
        model_name: Optional[str] = None,
    ) -> np.ndarray:
        if not self.is_fitted_:
            raise RuntimeError(f"Resource model for {self.target_name} is not fitted yet.")
        chosen = model_name or self.best_model_name_
        model = self.models_[chosen]
        if chosen in ("random_forest", "xgboost"):
            X_mat = X.to_numpy(dtype=float) if isinstance(X, FeatureMatrix) else np.asarray(X, dtype=float)
            if X_mat.ndim == 1:
                X_mat = X_mat.reshape(1, -1)
            preds = model.predict(X_mat)
        else:
            preds = model.predict(X)
        return np.maximum(self.min_value, np.asarray(preds, dtype=float))

    def predict_with_confidence(
        self,
        X_row: Union[FeatureMatrix, np.ndarray],
        shift_penalty: float = 1.0,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        point_pred = float(self.predict(X_row, model_name=model_name)[0])
        rf_model: RandomForestRegressor = self.models_["random_forest"]
        conf_info = self.confidence_estimator.estimate_single(
            rf_model=rf_model,
            X_row=X_row,
            point_prediction=point_pred,
            shift_penalty=shift_penalty,
        )
        return {
            "predicted_value": round(point_pred, 3),
            "expected_range": conf_info["expected_range"],
            "confidence": conf_info["confidence"],
            "confidence_pct": conf_info["confidence_pct"],
            "model_used": model_name or self.best_model_name_,
        }


class ResourcePredictor:
    """
    Coordinates CPU and Memory prediction models as well as optimal worker_count recommendation.
    """

    def __init__(self):
        self.cpu_model = SingleTargetResourceModel("actual_cpu", min_value=0.10)
        self.memory_model = SingleTargetResourceModel("actual_memory_mb", min_value=16.0)
        self.is_fitted_: bool = False

    def fit_and_evaluate(
        self,
        X: FeatureMatrix,
        y_cpu: np.ndarray,
        y_memory: np.ndarray,
        n_splits: int = 5,
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        cpu_metrics = self.cpu_model.fit_and_evaluate(X, y_cpu, n_splits=n_splits)
        mem_metrics = self.memory_model.fit_and_evaluate(X, y_memory, n_splits=n_splits)
        self.is_fitted_ = True
        return {
            "actual_cpu": cpu_metrics,
            "actual_memory_mb": mem_metrics,
        }

    def recommend_worker_count(
        self,
        feature_row: Dict[str, Any],
        predicted_runtime_1w: Optional[float] = None,
    ) -> int:
        """
        Recommend optimal worker count (1, 2, or 4) based on workload complexity and predicted runtime.
        """
        variants = float(feature_row.get("variant_count", 1170))
        samples = float(feature_row.get("sample_count", 100))
        genotypes_m = (variants * samples) / 1e6

        if predicted_runtime_1w is not None:
            if predicted_runtime_1w >= 3.5 or genotypes_m >= 25.0:
                return 4
            elif predicted_runtime_1w >= 0.75 or variants >= 10000:
                return 2
            return 1

        if variants >= 50000 or genotypes_m >= 25.0:
            return 4
        elif variants >= 10000 or genotypes_m >= 2.0:
            return 2
        return 1

    def predict_resources(
        self,
        X_row: Union[FeatureMatrix, np.ndarray],
        feature_dict: Dict[str, Any],
        shift_penalty: float = 1.0,
        predicted_runtime: Optional[float] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        cpu_res = self.cpu_model.predict_with_confidence(
            X_row, shift_penalty=shift_penalty, model_name=model_name
        )
        mem_res = self.memory_model.predict_with_confidence(
            X_row, shift_penalty=shift_penalty, model_name=model_name
        )
        rec_workers = self.recommend_worker_count(feature_dict, predicted_runtime_1w=predicted_runtime)

        return {
            "predicted_actual_cpu": round(cpu_res["predicted_value"], 3),
            "expected_cpu_range": cpu_res["expected_range"],
            "cpu_confidence": cpu_res["confidence"],
            "cpu_model_used": cpu_res["model_used"],
            "predicted_actual_memory_mb": round(mem_res["predicted_value"], 2),
            "expected_memory_range": (
                round(mem_res["expected_range"][0], 2),
                round(mem_res["expected_range"][1], 2),
            ),
            "memory_confidence": mem_res["confidence"],
            "memory_model_used": mem_res["model_used"],
            "recommended_worker_count": rec_workers,
        }
