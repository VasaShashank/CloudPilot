from typing import Dict, List, Union
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin

from backend.prediction.feature_pipeline import (
    CANONICAL_STAGE_TYPES,
    RAW_NUMERIC_FEATURES,
    STAGE_ONEHOT_FEATURES,
    FeatureMatrix,
)


class StageStatisticBaseline(BaseEstimator, RegressorMixin):
    """
    Baseline regressor that predicts the historical mean or median per genomic stage_type.
    Falls back to the global statistic if the stage type is unseen.
    """

    def __init__(self, stat: str = "mean"):
        self.stat = stat

    def _extract_stage_labels(self, X: Union[FeatureMatrix, np.ndarray]) -> List[str]:
        if isinstance(X, FeatureMatrix):
            arr = X[STAGE_ONEHOT_FEATURES].to_numpy(dtype=float)
        elif hasattr(X, "to_numpy"):
            raw = X.to_numpy(dtype=float)
            arr = raw[:, -len(CANONICAL_STAGE_TYPES):]
        else:
            raw = np.asarray(X, dtype=float)
            if raw.ndim == 1:
                raw = raw.reshape(1, -1)
            arr = raw[:, -len(CANONICAL_STAGE_TYPES):]

        labels: List[str] = []
        for row in arr:
            idx = int(np.argmax(row))
            if row[idx] > 0.5:
                labels.append(CANONICAL_STAGE_TYPES[idx])
            else:
                labels.append("unknown")
        return labels

    def fit(self, X: Union[FeatureMatrix, np.ndarray], y: np.ndarray) -> "StageStatisticBaseline":
        y_arr = np.asarray(y, dtype=float)
        if self.stat == "median":
            self.global_value_ = float(np.median(y_arr))
        else:
            self.global_value_ = float(np.mean(y_arr))

        labels = self._extract_stage_labels(X)
        self.stage_values_: Dict[str, float] = {}
        for st in CANONICAL_STAGE_TYPES:
            mask = np.array([lbl == st for lbl in labels], dtype=bool)
            if np.any(mask):
                if self.stat == "median":
                    self.stage_values_[st] = float(np.median(y_arr[mask]))
                else:
                    self.stage_values_[st] = float(np.mean(y_arr[mask]))
            else:
                self.stage_values_[st] = self.global_value_
        return self

    def predict(self, X: Union[FeatureMatrix, np.ndarray]) -> np.ndarray:
        labels = self._extract_stage_labels(X)
        preds = [self.stage_values_.get(lbl, self.global_value_) for lbl in labels]
        return np.array(preds, dtype=float)


class StageMeanBaseline(StageStatisticBaseline):
    """Predicts the historical mean for the given stage_type."""

    def __init__(self):
        super().__init__(stat="mean")


class StageMedianBaseline(StageStatisticBaseline):
    """Predicts the historical median for the given stage_type."""

    def __init__(self):
        super().__init__(stat="median")


class RidgeRegressionBaseline(BaseEstimator, RegressorMixin):
    """
    L2-regularized linear regression baseline operating on standardized raw workload + stage features.
    """

    def __init__(self, alpha: float = 1.0, min_clip: float = 0.05):
        self.alpha = alpha
        self.min_clip = min_clip

    def _select_columns(self, X: Union[FeatureMatrix, np.ndarray]) -> np.ndarray:
        linear_columns = RAW_NUMERIC_FEATURES + STAGE_ONEHOT_FEATURES
        if isinstance(X, FeatureMatrix):
            avail = [c for c in linear_columns if c in X.columns]
            if avail:
                return X[avail].to_numpy(dtype=float)
            return X.to_numpy(dtype=float)
        elif hasattr(X, "columns"):
            avail = [c for c in linear_columns if c in X.columns]
            if avail:
                return X[avail].to_numpy(dtype=float)
            return X.to_numpy(dtype=float)
        arr = np.asarray(X, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr

    def fit(self, X: Union[FeatureMatrix, np.ndarray], y: np.ndarray) -> "RidgeRegressionBaseline":
        X_mat = self._select_columns(X)
        y_arr = np.asarray(y, dtype=float)

        self.mean_ = np.mean(X_mat, axis=0)
        std = np.std(X_mat, axis=0)
        self.std_ = np.where(std < 1e-8, 1.0, std)

        X_scaled = (X_mat - self.mean_) / self.std_
        self.intercept_ = float(np.mean(y_arr))
        y_centered = y_arr - self.intercept_

        n_features = X_scaled.shape[1]
        A = X_scaled.T @ X_scaled + self.alpha * np.eye(n_features)
        b = X_scaled.T @ y_centered
        self.weights_ = np.linalg.solve(A, b)
        return self

    def predict(self, X: Union[FeatureMatrix, np.ndarray]) -> np.ndarray:
        X_mat = self._select_columns(X)
        X_scaled = (X_mat - self.mean_) / self.std_
        preds = self.intercept_ + X_scaled @ self.weights_
        return np.maximum(self.min_clip, preds)
