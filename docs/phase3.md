# CloudPilot — Phase 3: Predictive Intelligence Layer

## 1. Overview

Phase 3 implements the **Predictive Intelligence Layer** for CloudPilot. Before executing a genomic workflow stage on Kubernetes, CloudPilot predicts its runtime, CPU requirement, memory footprint, and optimal worker count, while estimating prediction confidence and detecting out-of-distribution (OOD) workloads.

---

## 2. Implemented Components

| Component | File | Purpose |
| :--- | :--- | :--- |
| **Feature Pipeline** | `backend/prediction/feature_pipeline.py` | Extracts 18 numeric, interaction, and one-hot stage features from raw genomic metadata and stage definitions. |
| **Statistical & Linear Baselines** | `backend/prediction/baseline.py` | Implements `StageMeanBaseline`, `StageMedianBaseline`, and `RidgeRegressionBaseline`. |
| **Runtime Predictor** | `backend/prediction/runtime_model.py` | 5-Fold CV trainer and predictor for `runtime_seconds` using `RandomForestRegressor` and `XGBRegressor`. |
| **Resource Predictor** | `backend/prediction/resource_model.py` | Predicts `actual_cpu`, `actual_memory_mb`, and recommends optimal `worker_count` (`1`, `2`, or `4`). |
| **Confidence Estimator** | `backend/prediction/confidence.py` | Calculates prediction intervals (`[low, high]`) and normalized confidence scores (`0–100%`) from Random Forest tree variance. |
| **Distribution-Shift Detector** | `backend/prediction/drift.py` | Combines domain boundary checks and log-space **Mahalanobis distance** to classify workloads as `NORMAL`, `WARNING`, or `SHIFTED`. |
| **Unified Intelligence Engine** | `backend/prediction/predictor.py` | `CloudPilotPredictor` facade for single-stage and full-DAG critical-path predictions. |
| **Training & Benchmark CLI** | `scripts/train_models.py` | Trains all 15 models (5 algorithms × 3 targets), outputs 5-fold CV leaderboards, and saves artifacts to `models/`. |

---

## 3. 5-Fold Cross-Validation Benchmark Results (`datasets/genomic_execution_history.csv`, $N=90$)

### Target 1: `runtime_seconds` (s)
| Model | MAE (s) | RMSE (s) | MAPE (%) | $R^2$ Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage Mean Baseline** | 2.4194 | 3.7747 | 273.57% | 0.0420 | Statistical Baseline |
| **Stage Median Baseline** | 2.1271 | 4.1035 | 109.79% | -0.1322 | Statistical Baseline |
| **Ridge Regression (Linear)** | 1.3083 | 2.4880 | 112.20% | 0.5838 | Linear Baseline |
| **Random Forest Regressor** | 0.7298 | 1.8738 | 26.18% | 0.7639 | Ensemble Bagging |
| **XGBoost (Default)** | 0.4611 | 1.3687 | 10.84% | 0.8741 | Untuned Winner |
| **Tuned XGBoost (HPO)** | **0.3577** | **1.3375** | **8.69%** | **0.8797** | **★ HPO BEST (-22.42% MAE)** |

### Target 2: `actual_cpu` (cores)
| Model | MAE (cores) | RMSE (cores) | MAPE (%) | $R^2$ Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage Mean Baseline** | 0.2986 | 0.3668 | 63.86% | -0.0474 | Statistical Baseline |
| **Stage Median Baseline** | 0.2927 | 0.3857 | 53.84% | -0.1578 | Statistical Baseline |
| **Ridge Regression (Linear)** | 0.1707 | 0.2096 | 35.94% | 0.6581 | Linear Baseline |
| **Random Forest Regressor** | 0.0804 | 0.1293 | 17.58% | 0.8698 | Ensemble Bagging |
| **XGBoost (Default)** | 0.0202 | 0.0339 | 3.51% | 0.9910 | Untuned Winner |
| **Tuned XGBoost (HPO)** | **0.0180** | **0.0296** | **2.94%** | **0.9932** | **★ HPO BEST (-10.89% MAE)** |

### Target 3: `actual_memory_mb` (MB)
| Model | MAE (MB) | RMSE (MB) | MAPE (%) | $R^2$ Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage Mean Baseline** | 47.7506 | 67.4747 | 80.50% | -0.2073 | Statistical Baseline |
| **Stage Median Baseline** | 41.1438 | 66.5548 | 52.83% | -0.1746 | Statistical Baseline |
| **Ridge Regression (Linear)** | 4.9707 | 6.7991 | 8.46% | 0.9877 | Linear Baseline |
| **Random Forest Regressor** | 7.5356 | 11.4294 | 11.41% | 0.9654 | Ensemble Bagging |
| **XGBoost (Default)** | 4.5735 | 6.9908 | 6.20% | 0.9870 | Untuned Winner |
| **Tuned XGBoost (HPO)** | **4.3496** | **6.9592** | **5.56%** | **0.9872** | **★ HPO BEST (-4.90% MAE)** |

---

## 4. Hyperparameter Optimization (HPO) Summary

Hyperparameter tuning was conducted on the winning untuned model architecture (`xgboost`) using 5-Fold Cross-Validation grid search across learning rate, tree depth, estimator count, subsampling ratio, column sampling, and L1/L2 regularization penalties:

| Target | Base Winner | Trials | MAE Before | MAE After | MAE Improvement | $R^2$ Gain | Optimal Hyperparameters (`best_params`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`runtime_seconds`** | XGBoost | 12 | 0.4611s | **0.3577s** | **-22.42%** | +0.0056 | `n_estimators=120`, `max_depth=4`, `learning_rate=0.05`, `subsample=0.9`, `colsample_bytree=1.0`, `reg_alpha=0.0`, `reg_lambda=0.5` |
| **`actual_cpu`** | XGBoost | 12 | 0.0202 cores | **0.0180 cores** | **-10.89%** | +0.0022 | `n_estimators=100`, `max_depth=3`, `learning_rate=0.06`, `subsample=0.9`, `colsample_bytree=0.95`, `reg_alpha=0.02`, `reg_lambda=0.8` |
| **`actual_memory_mb`** | XGBoost | 12 | 4.5735 MB | **4.3496 MB** | **-4.90%** | +0.0002 | `n_estimators=150`, `max_depth=3`, `learning_rate=0.06`, `subsample=0.95`, `colsample_bytree=0.95`, `reg_alpha=0.0`, `reg_lambda=0.5` |

---

## 5. Exported CSV Evaluation & Benchmark Files

All evaluation artifacts are saved in both `datasets/` and `models/` for direct inspection in Excel, pandas, or GitHub:

1. **`datasets/hyperparameter_optimization_results.csv`**: Before vs after HPO metrics, percentage improvements, and winning hyperparameter sets.
2. **`datasets/model_evaluation_results.csv`**: Complete 5-fold CV leaderboards comparing all 6 models across MAE, RMSE, MAPE, and $R^2$.
3. **`datasets/model_predictions_comparison.csv`**: Row-by-row prediction comparison for all 90 historical genomic runs across all 6 models against ground truth.
4. **`datasets/distribution_shift_test_results.csv`**: Validation runs across normal, borderline, and out-of-distribution (OOD) test workloads verifying Mahalanobis shift detection and confidence penalties.

---

## 6. Reproducibility Commands

```bash
# Train, cross-validate, optimize hyperparameters, and export CSV leaderboards
.\.venv\Scripts\python.exe scripts/train_models.py

# Predict an entire workflow DAG from the CLI
.\.venv\Scripts\python.exe backend/main.py predict workflows/genomic_pipeline.yaml

# Run automated test suite (59 tests)
.\.venv\Scripts\python.exe -m pytest -v
```

