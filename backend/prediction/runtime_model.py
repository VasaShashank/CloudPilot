from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, ParameterGrid
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
    """Return the 5 initial candidate models in the Phase 3 model progression."""
    return {
        "stage_mean": StageMeanBaseline(),
        "stage_median": StageMedianBaseline(),
        "ridge_regression": RidgeRegressionBaseline(alpha=1.0, min_clip=min_clip),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=6,
            min_samples_split=3,
            min_samples_leaf=2,
            max_features="sqrt",
            random_state=42,
        ),
        "xgboost": XGBRegressor(
            n_estimators=80,
            max_depth=3,
            learning_rate=0.10,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=1.5,
            random_state=42,
            verbosity=0,
        ),
    }


def get_hpo_search_space(model_family: str) -> List[Dict[str, Any]]:
    """Return targeted, high-impact hyperparameter search configurations for the selected model family."""
    if model_family == "random_forest":
        return [
            {"n_estimators": 60, "max_depth": 5, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": "sqrt"},
            {"n_estimators": 80, "max_depth": 6, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": 0.8},
            {"n_estimators": 100, "max_depth": 6, "min_samples_split": 3, "min_samples_leaf": 2, "max_features": "sqrt"},
            {"n_estimators": 120, "max_depth": 8, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": 1.0},
            {"n_estimators": 140, "max_depth": 8, "min_samples_split": 3, "min_samples_leaf": 1, "max_features": 0.8},
            {"n_estimators": 160, "max_depth": 10, "min_samples_split": 2, "min_samples_leaf": 2, "max_features": "sqrt"},
            {"n_estimators": 100, "max_depth": None, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": "sqrt"},
            {"n_estimators": 120, "max_depth": None, "min_samples_split": 3, "min_samples_leaf": 2, "max_features": 0.8},
            {"n_estimators": 150, "max_depth": None, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": 1.0},
            {"n_estimators": 80, "max_depth": 4, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": "sqrt"},
            {"n_estimators": 100, "max_depth": 7, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": "sqrt"},
            {"n_estimators": 130, "max_depth": 9, "min_samples_split": 2, "min_samples_leaf": 1, "max_features": 0.9},
        ]
    elif model_family == "xgboost":
        return [
            {"n_estimators": 80, "max_depth": 3, "learning_rate": 0.08, "subsample": 0.9, "colsample_bytree": 0.9, "reg_alpha": 0.05, "reg_lambda": 1.0},
            {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.06, "subsample": 0.9, "colsample_bytree": 0.95, "reg_alpha": 0.02, "reg_lambda": 0.8},
            {"n_estimators": 120, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 1.0, "reg_alpha": 0.0, "reg_lambda": 0.5},
            {"n_estimators": 140, "max_depth": 3, "learning_rate": 0.05, "subsample": 0.85, "colsample_bytree": 0.85, "reg_alpha": 0.1, "reg_lambda": 1.5},
            {"n_estimators": 160, "max_depth": 4, "learning_rate": 0.04, "subsample": 0.95, "colsample_bytree": 0.9, "reg_alpha": 0.05, "reg_lambda": 1.0},
            {"n_estimators": 90, "max_depth": 2, "learning_rate": 0.10, "subsample": 0.9, "colsample_bytree": 0.9, "reg_alpha": 0.0, "reg_lambda": 1.0},
            {"n_estimators": 110, "max_depth": 3, "learning_rate": 0.10, "subsample": 0.85, "colsample_bytree": 0.85, "reg_alpha": 0.05, "reg_lambda": 0.8},
            {"n_estimators": 130, "max_depth": 4, "learning_rate": 0.07, "subsample": 0.9, "colsample_bytree": 0.9, "reg_alpha": 0.02, "reg_lambda": 1.2},
            {"n_estimators": 150, "max_depth": 3, "learning_rate": 0.06, "subsample": 0.95, "colsample_bytree": 0.95, "reg_alpha": 0.0, "reg_lambda": 0.5},
            {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.04, "subsample": 0.85, "colsample_bytree": 0.85, "reg_alpha": 0.1, "reg_lambda": 1.0},
            {"n_estimators": 70, "max_depth": 3, "learning_rate": 0.12, "subsample": 0.9, "colsample_bytree": 0.9, "reg_alpha": 0.02, "reg_lambda": 1.0},
            {"n_estimators": 120, "max_depth": 3, "learning_rate": 0.07, "subsample": 0.9, "colsample_bytree": 0.95, "reg_alpha": 0.01, "reg_lambda": 0.7},
        ]
    return []



def run_kfold_hpo(
    model_family: str,
    X_mat: np.ndarray,
    y_arr: np.ndarray,
    kf: KFold,
    min_clip: float,
    baseline_metrics: Dict[str, float],
    baseline_estimator: Any,
) -> Tuple[Any, Dict[str, Any], Dict[str, float], Dict[str, Any]]:
    """
    Perform 5-Fold Cross-Validation Hyperparameter Optimization on the winning model family.
    Returns:
    - fitted_best_estimator (trained on full X_mat, y_arr)
    - best_params dict
    - best_cv_metrics dict
    - hpo_summary dict (before vs after comparison)
    """
    param_list = get_hpo_search_space(model_family)
    best_mae = float(baseline_metrics["mae"])
    best_rmse = float(baseline_metrics["rmse"])
    best_metrics = dict(baseline_metrics)
    best_params: Dict[str, Any] = {}
    best_template = clone(baseline_estimator)

    # Extract default params from baseline_estimator in case no candidate improves
    for k in (
        "n_estimators",
        "max_depth",
        "min_samples_split",
        "min_samples_leaf",
        "max_features",
        "learning_rate",
        "subsample",
        "colsample_bytree",
        "reg_alpha",
        "reg_lambda",
    ):
        if hasattr(baseline_estimator, k):
            best_params[k] = getattr(baseline_estimator, k)

    for params in param_list:
        if model_family == "random_forest":
            cand = RandomForestRegressor(random_state=42, **params)
        else:
            cand = XGBRegressor(random_state=42, verbosity=0, **params)

        oof_preds = np.zeros_like(y_arr, dtype=float)
        for train_idx, val_idx in kf.split(X_mat):
            m = clone(cand)
            m.fit(X_mat[train_idx], y_arr[train_idx])
            preds = m.predict(X_mat[val_idx])
            oof_preds[val_idx] = np.maximum(min_clip, preds)

        metrics = compute_regression_metrics(y_arr, oof_preds)
        if (metrics["mae"] < best_mae) or (
            abs(metrics["mae"] - best_mae) < 1e-6 and metrics["rmse"] < best_rmse
        ):
            best_mae = metrics["mae"]
            best_rmse = metrics["rmse"]
            best_metrics = metrics
            best_params = dict(params)
            best_template = cand

    fitted_best = clone(best_template)
    fitted_best.fit(X_mat, y_arr)

    mae_before = float(baseline_metrics["mae"])
    mae_after = float(best_metrics["mae"])
    rmse_before = float(baseline_metrics["rmse"])
    rmse_after = float(best_metrics["rmse"])

    mae_imp_pct = round(((mae_before - mae_after) / max(mae_before, 1e-6)) * 100.0, 2)
    rmse_imp_pct = round(((rmse_before - rmse_after) / max(rmse_before, 1e-6)) * 100.0, 2)
    r2_gain = round(float(best_metrics["r2"]) - float(baseline_metrics["r2"]), 4)

    hpo_summary = {
        "base_model_family": model_family,
        "trials_evaluated": len(param_list),
        "best_params": best_params,
        "before_hpo": baseline_metrics,
        "after_hpo": best_metrics,
        "mae_improvement_pct": mae_imp_pct,
        "rmse_improvement_pct": rmse_imp_pct,
        "r2_gain": r2_gain,
    }
    return fitted_best, best_params, best_metrics, hpo_summary


class RuntimePredictor:
    """
    Trains, benchmarks, and serves the runtime_seconds predictive model progression:
    Stage Mean -> Stage Median -> Ridge Regression -> Random Forest -> XGBoost
    followed by Hyperparameter Optimization (HPO) on the best model.
    """

    def __init__(self, min_runtime: float = 0.1):
        self.min_runtime = min_runtime
        self.models_: Dict[str, Any] = {}
        self.cv_metrics_: Dict[str, Dict[str, float]] = {}
        self.untuned_best_model_name_: str = "random_forest"
        self.best_model_name_: str = "tuned_best"
        self.best_params_: Dict[str, Any] = {}
        self.hpo_summary_: Dict[str, Any] = {}
        self.confidence_estimator = ConfidenceEstimator(gamma=0.60, min_floor=min_runtime)
        self.is_fitted_: bool = False

    def fit_and_evaluate(
        self, X: FeatureMatrix, y: np.ndarray, n_splits: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Perform K-Fold Cross-Validation across all 5 model tiers, select the best model,
        and run Hyperparameter Optimization (HPO) to produce the final tuned model.
        """
        y_arr = np.asarray(y, dtype=float)
        X_mat = X.to_numpy(dtype=float)
        candidates = build_candidate_models(min_clip=self.min_runtime)
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

        self.cv_metrics_ = {}
        self.models_ = {}

        for name, base_model in candidates.items():
            oof_preds = np.zeros_like(y_arr, dtype=float)
            for train_idx, val_idx in kf.split(X_mat):
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
                fitted_model.fit(X_mat, y_arr)
            else:
                fitted_model.fit(X, y_arr)
            self.models_[name] = fitted_model

        # 1. Identify best untuned model
        self.untuned_best_model_name_ = min(
            self.cv_metrics_.keys(), key=lambda k: self.cv_metrics_[k]["mae"]
        )

        # 2. Perform Hyperparameter Optimization on the winning ML architecture
        target_family = (
            self.untuned_best_model_name_
            if self.untuned_best_model_name_ in ("random_forest", "xgboost")
            else "xgboost"
        )
        tuned_model, best_params, tuned_metrics, hpo_info = run_kfold_hpo(
            model_family=target_family,
            X_mat=X_mat,
            y_arr=y_arr,
            kf=kf,
            min_clip=self.min_runtime,
            baseline_metrics=self.cv_metrics_[target_family],
            baseline_estimator=candidates[target_family],
        )

        # Also tune Random Forest if XGBoost was the winner so confidence intervals use an optimized forest
        if target_family != "random_forest":
            tuned_rf, _, _, _ = run_kfold_hpo(
                model_family="random_forest",
                X_mat=X_mat,
                y_arr=y_arr,
                kf=kf,
                min_clip=self.min_runtime,
                baseline_metrics=self.cv_metrics_["random_forest"],
                baseline_estimator=candidates["random_forest"],
            )
            self.models_["tuned_random_forest"] = tuned_rf
        else:
            self.models_["tuned_random_forest"] = tuned_model

        self.models_["tuned_best"] = tuned_model
        self.cv_metrics_["tuned_best"] = tuned_metrics
        self.best_params_ = best_params
        self.hpo_summary_ = hpo_info
        self.best_model_name_ = "tuned_best"
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
        if chosen in ("random_forest", "xgboost", "tuned_best", "tuned_random_forest"):
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
        rf_model: RandomForestRegressor = self.models_.get(
            "tuned_random_forest", self.models_["random_forest"]
        )
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
            "model_used": model_name or f"tuned_{self.untuned_best_model_name_}",
        }
