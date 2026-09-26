from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.prediction.feature_pipeline import (
    CANONICAL_STAGE_TYPES,
    RAW_NUMERIC_FEATURES,
    FeatureMatrix,
    normalize_stage_type,
)


class ShiftStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    SHIFTED = "SHIFTED"


SHIFT_MONITORED_FEATURES = [
    "region_size",
    "variant_count",
    "sample_count",
    "dataset_size_mb",
]


class DistributionShiftDetector:
    """
    Detects out-of-distribution (OOD) genomic workloads using:
    1. Domain Boundary Checks against historical training min/max ranges
    2. Multivariate Mahalanobis Distance in log-scaled feature space
    """

    def __init__(
        self,
        warning_multiplier: float = 1.25,
        shifted_multiplier: float = 2.0,
        mahalanobis_warn: float = 3.5,
        mahalanobis_shift: float = 5.5,
    ):
        self.warning_multiplier = warning_multiplier
        self.shifted_multiplier = shifted_multiplier
        self.mahalanobis_warn = mahalanobis_warn
        self.mahalanobis_shift = mahalanobis_shift

        self.feature_bounds_: Dict[str, Tuple[float, float]] = {}
        self.known_stages_: set[str] = set(CANONICAL_STAGE_TYPES)
        self.mean_: Optional[np.ndarray] = None
        self.inv_cov_: Optional[np.ndarray] = None
        self.is_fitted_: bool = False

    def _to_log_matrix(self, data: Union[FeatureMatrix, List[Dict[str, Any]], Dict[str, Any], np.ndarray]) -> np.ndarray:
        if isinstance(data, dict):
            rows = [data]
            mat = np.array([[float(r.get(f, 0.0)) for f in SHIFT_MONITORED_FEATURES] for r in rows], dtype=float)
        elif isinstance(data, list):
            mat = np.array([[float(r.get(f, 0.0)) for f in SHIFT_MONITORED_FEATURES] for r in data], dtype=float)
        elif isinstance(data, FeatureMatrix):
            mat = data[SHIFT_MONITORED_FEATURES].to_numpy(dtype=float)
        elif hasattr(data, "columns"):
            mat = data[SHIFT_MONITORED_FEATURES].to_numpy(dtype=float)
        else:
            mat = np.asarray(data, dtype=float)
            if mat.ndim == 1:
                mat = mat.reshape(1, -1)

        return np.log1p(np.maximum(0.0, mat))

    def fit(self, X: FeatureMatrix) -> "DistributionShiftDetector":
        """Fit boundary ranges and multivariate Gaussian parameters on training features."""
        self.feature_bounds_ = {}
        for col in RAW_NUMERIC_FEATURES:
            if col in X.columns:
                vals = np.asarray(X[col], dtype=float)
                self.feature_bounds_[col] = (float(np.min(vals)), float(np.max(vals)))

        log_mat = self._to_log_matrix(X)
        self.mean_ = np.mean(log_mat, axis=0)
        cov = np.cov(log_mat, rowvar=False)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        reg_cov = cov + np.eye(cov.shape[0]) * 1e-3
        self.inv_cov_ = np.linalg.inv(reg_cov)

        train_dists = self._compute_mahalanobis_batch(log_mat)
        max_train_dist = float(np.max(train_dists)) if len(train_dists) > 0 else 2.5
        self.mahalanobis_warn = max(self.mahalanobis_warn, round(max_train_dist * 1.15, 3))
        self.mahalanobis_shift = max(self.mahalanobis_shift, round(max_train_dist * 1.75, 3))

        self.is_fitted_ = True
        return self

    def _compute_mahalanobis_batch(self, log_mat: np.ndarray) -> np.ndarray:
        diffs = log_mat - self.mean_
        left = np.dot(diffs, self.inv_cov_)
        mahal_sq = np.sum(left * diffs, axis=1)
        return np.sqrt(np.maximum(0.0, mahal_sq))

    def evaluate_single(self, feature_row: Dict[str, Any], raw_stage_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate a single stage/workload feature dictionary for distribution shift.
        Returns status (NORMAL, WARNING, SHIFTED), Mahalanobis distance, reasons, and confidence penalty.
        """
        if not self.is_fitted_:
            raise RuntimeError("DistributionShiftDetector must be fitted before calling evaluate_single.")

        reasons: List[str] = []
        out_of_bounds_features: List[str] = []
        severity = ShiftStatus.NORMAL

        if raw_stage_type is not None:
            norm_stage = normalize_stage_type(raw_stage_type)
            if norm_stage not in self.known_stages_:
                severity = ShiftStatus.SHIFTED
                reasons.append(f"Unseen stage_type '{raw_stage_type}'")

        for feat in SHIFT_MONITORED_FEATURES:
            if feat not in self.feature_bounds_ or feat not in feature_row:
                continue
            val = float(feature_row[feat])
            f_min, f_max = self.feature_bounds_[feat]

            if val > f_max * self.shifted_multiplier or (f_min > 0 and val < f_min / self.shifted_multiplier):
                severity = ShiftStatus.SHIFTED
                out_of_bounds_features.append(feat)
                reasons.append(
                    f"{feat}={val:g} severely outside training range [{f_min:g}, {f_max:g}]"
                )
            elif val > f_max * self.warning_multiplier or (f_min > 0 and val < f_min / self.warning_multiplier):
                if severity != ShiftStatus.SHIFTED:
                    severity = ShiftStatus.WARNING
                out_of_bounds_features.append(feat)
                reasons.append(
                    f"{feat}={val:g} near/beyond training boundary [{f_min:g}, {f_max:g}]"
                )

        log_vec = self._to_log_matrix(feature_row)
        dist = float(self._compute_mahalanobis_batch(log_vec)[0])

        if dist > self.mahalanobis_shift:
            severity = ShiftStatus.SHIFTED
            reasons.append(
                f"Mahalanobis distance {dist:.2f} exceeds shift threshold ({self.mahalanobis_shift:.2f})"
            )
        elif dist > self.mahalanobis_warn:
            if severity != ShiftStatus.SHIFTED:
                severity = ShiftStatus.WARNING
            reasons.append(
                f"Mahalanobis distance {dist:.2f} exceeds warning threshold ({self.mahalanobis_warn:.2f})"
            )

        if severity == ShiftStatus.NORMAL:
            penalty = 1.0
        elif severity == ShiftStatus.WARNING:
            penalty = max(0.68, 0.85 - 0.03 * max(0.0, dist - self.mahalanobis_warn))
        else:
            penalty = max(0.25, 0.50 - 0.02 * max(0.0, dist - self.mahalanobis_shift))

        return {
            "status": severity.value,
            "mahalanobis_distance": round(dist, 3),
            "out_of_bounds_features": out_of_bounds_features,
            "reasons": reasons,
            "confidence_penalty": round(float(penalty), 4),
            "fallback_recommended": severity == ShiftStatus.SHIFTED,
        }
