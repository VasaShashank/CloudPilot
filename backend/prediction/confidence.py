from typing import Any, Dict, Optional, Union
import numpy as np

from backend.prediction.feature_pipeline import FeatureMatrix


class ConfidenceEstimator:
    """
    Computes prediction confidence scores and expected prediction intervals using:
    1. Ensemble variance across individual trees in Random Forest (rf_model.estimators_)
    2. Extrapolation / distribution-shift penalty for out-of-domain inputs
    """

    def __init__(self, gamma: float = 0.60, min_floor: float = 0.05):
        self.gamma = gamma
        self.min_floor = min_floor

    def estimate_from_forest(
        self,
        rf_model: Any,
        X: Union[FeatureMatrix, np.ndarray],
        point_predictions: Optional[np.ndarray] = None,
        shift_penalties: Optional[np.ndarray] = None,
    ) -> list[Dict[str, Any]]:
        """
        Evaluate tree-level predictions for each sample in X and return:
        - confidence: float in [0.05, 0.99]
        - confidence_pct: float in [5.0, 99.0]
        - ensemble_std: float ensemble standard deviation
        - cv: float coefficient of variation
        - expected_range: (low, high) tuple around the point prediction
        """
        if isinstance(X, FeatureMatrix):
            X_mat = X.to_numpy(dtype=float)
        else:
            X_mat = np.asarray(X, dtype=float)

        if X_mat.ndim == 1:
            X_mat = X_mat.reshape(1, -1)

        # Collect predictions from each decision tree in the forest
        tree_preds = np.array([tree.predict(X_mat) for tree in rf_model.estimators_], dtype=float)

        means = np.mean(tree_preds, axis=0)
        stds = np.std(tree_preds, axis=0)

        if point_predictions is None:
            centers = means
        else:
            centers = np.asarray(point_predictions, dtype=float)

        results = []
        for i in range(X_mat.shape[0]):
            center = float(max(self.min_floor, centers[i]))
            mean_val = float(max(self.min_floor, means[i]))
            std_val = float(stds[i])

            cv = std_val / max(mean_val, 0.1)
            base_conf = 1.0 / (1.0 + self.gamma * cv)

            penalty = float(shift_penalties[i]) if shift_penalties is not None else 1.0
            conf = float(np.clip(base_conf * penalty, 0.05, 0.99))

            margin_ratio = max(0.08, min(0.75, 1.28 * cv + (1.0 - penalty) * 0.5))
            half_width = max(std_val * 1.28, center * margin_ratio)
            low = round(max(self.min_floor, center - half_width), 3)
            high = round(center + half_width, 3)

            results.append(
                {
                    "confidence": round(conf, 4),
                    "confidence_pct": round(conf * 100.0, 1),
                    "ensemble_std": round(std_val, 4),
                    "cv": round(cv, 4),
                    "expected_range": (low, high),
                }
            )
        return results

    def estimate_single(
        self,
        rf_model: Any,
        X_row: Union[FeatureMatrix, np.ndarray],
        point_prediction: Optional[float] = None,
        shift_penalty: float = 1.0,
    ) -> Dict[str, Any]:
        pts = np.array([point_prediction]) if point_prediction is not None else None
        pens = np.array([shift_penalty])
        return self.estimate_from_forest(rf_model, X_row, point_predictions=pts, shift_penalties=pens)[0]
