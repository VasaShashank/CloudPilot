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

### Target 1: `runtime_seconds`
| Model | MAE (s) | RMSE (s) | MAPE (%) | $R^2$ Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage Mean Baseline** | 2.4194 | 3.7747 | 273.57% | 0.0420 | Baseline |
| **Stage Median Baseline** | 2.1271 | 4.1035 | 109.79% | -0.1322 | Baseline |
| **Ridge Regression (Linear)** | 1.3083 | 2.4880 | 112.20% | 0.5838 | Linear |
| **Random Forest Regressor** | **0.4104** | 1.4021 | **8.36%** | 0.8678 | **★ BEST (MAE)** |
| **XGBoost Regressor** | 0.4396 | **1.3494** | 9.53% | **0.8776** | **★ BEST ($R^2$)** |

### Target 2: `actual_cpu` (cores)
| Model | MAE (cores) | RMSE (cores) | MAPE (%) | $R^2$ Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage Mean Baseline** | 0.2986 | 0.3668 | 63.86% | -0.0474 | Baseline |
| **Stage Median Baseline** | 0.2927 | 0.3857 | 53.84% | -0.1578 | Baseline |
| **Ridge Regression (Linear)** | 0.1707 | 0.2096 | 35.94% | 0.6581 | Linear |
| **Random Forest Regressor** | 0.0212 | 0.0427 | **2.82%** | 0.9858 | Ensemble |
| **XGBoost Regressor** | **0.0193** | **0.0318** | 3.25% | **0.9921** | **★ BEST** |

### Target 3: `actual_memory_mb` (MB)
| Model | MAE (MB) | RMSE (MB) | MAPE (%) | $R^2$ Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage Mean Baseline** | 47.7506 | 67.4747 | 80.50% | -0.2073 | Baseline |
| **Stage Median Baseline** | 41.1438 | 66.5548 | 52.83% | -0.1746 | Baseline |
| **Ridge Regression (Linear)** | 4.9707 | 6.7991 | 8.46% | 0.9877 | Linear |
| **Random Forest Regressor** | 5.5473 | 8.4043 | 7.54% | 0.9813 | Ensemble |
| **XGBoost Regressor** | **4.7274** | 7.7085 | **6.01%** | **0.9842** | **★ BEST** |

---

## 4. Reproducibility Commands

```bash
# Train and benchmark all Phase 3 models
.\.venv\Scripts\python.exe scripts/train_models.py

# Predict an entire workflow DAG from the CLI
.\.venv\Scripts\python.exe backend/main.py predict workflows/genomic_pipeline.yaml

# Run automated test suite
.\.venv\Scripts\pytest.exe -v
```
