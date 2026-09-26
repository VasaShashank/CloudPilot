from typing import Any, Dict, Optional, Union
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

from backend.prediction.baseline import (
    RidgeRegressionBaseline,
    StageMeanBaseline,
    StageMedianBaseline,
)
from backend.prediction.confidence import ConfidenceEstimator
from backend.prediction.feature_pipeline import FeatureMatrix


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, MAPE (%), and R² score."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
    denom = np.maximum(np.abs(y_t), 1e-3)
    mape = float(np.mean(np.abs(y_t - y_p) / denom) * 100.0)
    r2 = float(r2_score(y_t, y_p))
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape_pct": round(mape, 2),
        "r2": round(r2, 4),
    }


def build_candidate_models(min_clip: float = 0.05) -> Dict[str, Any]:
    """Return the 5 candidate models in the Phase 3 model progression."""
    return {
        "stage_mean": StageMeanBaseline(),
        "stage_median": StageMedianBaseline(),
        "ridge_regression": RidgeRegressionBaseline(alpha=1.0, min_clip=min_clip),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=1,
            random_state=42,
        ),
        "xgboost": XGBRegressor(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_alpha=0.05,
            reg_lambda=1.0,
            random_state=42,
            verbosity=0,
        ),
    }


class RuntimePredictor:
    """
    Trains, benchmarks, and serves the runtime_seconds predictive model progression:
    Stage Mean -> Stage Median -> Ridge Regression -> Random Forest -> XGBoost.
    """

    def __init__(self, min_runtime: float = 0.1):
        self.min_runtime = min_runtime
        self.models_: Dict[str, Any] = {}
        self.cv_metrics_: Dict[str, Dict[str, float]] = {}
        self.best_model_name_: str = "random_forest"
        self.confidence_estimator = ConfidenceEstimator(gamma=0.60, min_floor=min_runtime)
        self.is_fitted_: bool = False

    def fit_and_evaluate(
        self, X: FeatureMatrix, y: np.ndarray, n_splits: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Perform K-Fold Cross-Validation across all 5 model tiers, select the most accurate model,
        and fit all models on the complete training dataset.
        """
        y_arr = np.asarray(y, dtype=float)
        candidates = build_candidate_models(min_clip=self.min_runtime)
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

                oof_preds[val_idx] = np.maximum(self.min_runtime, preds)

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
            raise RuntimeError("RuntimePredictor is not fitted yet.")
        chosen = model_name or self.best_model_name_
        model = self.models_[chosen]
        if chosen in ("random_forest", "xgboost"):
            X_mat = X.to_numpy(dtype=float) if isinstance(X, FeatureMatrix) else np.asarray(X, dtype=float)
            if X_mat.ndim == 1:
                X_mat = X_mat.reshape(1, -1)
            preds = model.predict(X_mat)
        else:
            preds = model.predict(X)
        return np.maximum(self.min_runtime, np.asarray(preds, dtype=float))

    def predict_with_confidence(
        self,
        X_row: Union[FeatureMatrix, np.ndarray],
        shift_penalty: float = 1.0,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Predict runtime along with expected interval and confidence percentage."""
        point_pred = float(self.predict(X_row, model_name=model_name)[0])
        rf_model: RandomForestRegressor = self.models_["random_forest"]
        conf_info = self.confidence_estimator.estimate_single(
            rf_model=rf_model,
            X_row=X_row,
            point_prediction=point_pred,
            shift_penalty=shift_penalty,
        )
        return {
            "predicted_runtime_seconds": round(point_pred, 3),
            "expected_runtime_range": conf_info["expected_range"],
            "confidence": conf_info["confidence"],
            "confidence_pct": conf_info["confidence_pct"],
            "ensemble_std": conf_info["ensemble_std"],
            "model_used": model_name or self.best_model_name_,
        }
