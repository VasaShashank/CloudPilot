# CloudPilot — 5-Phase Implementation Plan
## Intelligent Predictive Resource Orchestration for Genomic Analysis Workflows on Kubernetes

> **Current dataset setup:** The 1000 Genomes Phase 3 chromosome 22 genotype VCF and its index are downloaded and stored locally under:
>
> `data/genomic/raw/`
>
> The `.vcf.gz` is compressed (196 MB). **Do not unzip it.** The `.tbi` index is kept beside it for fast regional extraction with `bcftools`/`tabix`.
>
> **Status Summary:**
> - **Phase 1 (Kubernetes Workflow Engine):** ✅ COMPLETED & VALIDATED (DAG execution, parallel branches, K8s Jobs).
> - **Phase 2 (Genomic Workload Profiling & Monitoring):** ✅ COMPLETED & VALIDATED (9 VCF chunks, sample variation, containerized bcftools, 20-column schema, 94 clean ML records).
<<<<<<< HEAD
> - **Phase 3 (Prediction & Intelligence):** ✅ COMPLETED & VALIDATED (Baseline models, Random Forest, XGBoost, confidence scoring, distribution shift detection).
> - **Phase 4 (Decision Engine & Intelligent Scheduling):** ✅ COMPLETED & VALIDATED (Dynamic K8s resource requests, SLA-aware scheduling, safe fallback).
> - **Phase 5 (Dashboard, Integration & Evaluation):** 🔄 ACTIVE NEXT STEP (FastAPI Web UI, visual DAG execution, 3-way quantitative evaluation).
=======
> - **Phase 3 (Prediction & Intelligence):** 🔄 ACTIVE NEXT STEP (Baseline models, Random Forest, XGBoost, confidence scoring, distribution shift detection).
> - **Phase 4 (Decision Engine & Intelligent Scheduling):** 📋 PLANNED (Dynamic K8s resource requests, SLA-aware scheduling, safe fallback).
> - **Phase 5 (Dashboard, Integration & Evaluation):** 📋 PLANNED (FastAPI Web UI, visual DAG execution, 3-way quantitative evaluation).
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

---

# 1. Project Objective

CloudPilot is an intelligent Kubernetes-based orchestration platform for genomic analysis workflows.

The system will:

1. Accept a workflow represented as a DAG.
2. Validate dependencies and execution order.
3. Execute workflow stages as Kubernetes Jobs.
4. Collect workload characteristics and execution metrics.
5. Build a historical execution dataset.
6. Predict runtime and resource requirements.
7. Estimate prediction confidence.
8. Detect distribution shift when a workload differs from historical data.
9. Make SLA/deadline-aware resource allocation decisions.
10. Dynamically schedule workloads on Kubernetes.
11. Monitor execution and compare predicted versus actual behavior.
12. Provide a dashboard for workflow submission, monitoring, prediction visibility, and evaluation.

The project is divided into **5 meaningful phases** rather than many small implementation stages.

---

# 2. Five-Phase Overview

| Phase | Name | Status | Main Outcome |
|---|---|---|---|
| 1 | Kubernetes Workflow Engine | ✅ Complete | Parallel DAG executes reliably as Kubernetes Jobs on kind cluster |
| 2 | Genomic Workload Profiling & Monitoring | ✅ Complete | Real genomic workloads produce structured, varied 20-column execution dataset |
<<<<<<< HEAD
| 3 | Prediction & Intelligence | ✅ Complete | CloudPilot predicts runtime/resources and evaluates confidence/shift using Phase 2 data |
| 4 | Decision Engine & Intelligent Scheduling | ✅ Complete | Predictions and confidence become dynamic Kubernetes resource/scheduling decisions |
| 5 | Dashboard, Integration & Evaluation | 🔄 Active Next | Complete CloudPilot system is visualized via Web UI and quantitatively evaluated |
=======
| 3 | Prediction & Intelligence | 🔄 Active Next | CloudPilot predicts runtime/resources and evaluates confidence/shift using Phase 2 data |
| 4 | Decision Engine & Intelligent Scheduling | 📋 Planned | Predictions and confidence become dynamic Kubernetes resource/scheduling decisions |
| 5 | Dashboard, Integration & Evaluation | 📋 Planned | Complete CloudPilot system is visualized via Web UI and quantitatively evaluated |
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

---

# 3. Recommended Technology Stack

## Core

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic v2
- NetworkX
- PyYAML
- Kubernetes Python client
- Docker
- Kubernetes (kind)
- WSL2 + Ubuntu / Windows
- Git / GitHub

## Data and genomic processing

- VCF / VCF.GZ (bgzip compressed)
- Tabix index (`.tbi`)
- bcftools 1.21+
- tabix 1.21+
- pandas
- NumPy

## Monitoring

- Container cgroups / psutil telemetry
- Kubernetes metrics API
- Prometheus (optional / Phase 5 integration)

## Machine Learning (Phase 3)

- scikit-learn
- XGBoost
- joblib
- scipy (statistical distance / Mahalanobis)

## Frontend / visualization (Phase 5)

- FastAPI backend + static UI
- HTML5 / CSS3 / Vanilla JS
- SVG / Cytoscape.js for DAG visualization
- Chart.js / Plotly for telemetry dashboards

---

# 4. Current Project Structure

```text
cloudpilot/
│
├── backend/
│   ├── main.py                    # FastAPI entrypoint + CLI runner
│   ├── config.py                  # Cluster and engine constants
│   │
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── parser.py              # YAML workflow parsing
│   │   ├── validator.py           # Dependency & cycle validation
│   │   └── dag.py                 # NetworkX DAG graph operations
│   │
│   ├── k8s/
│   │   ├── __init__.py
│   │   ├── client.py              # Local kubeconfig + in-cluster fallback
│   │   ├── job_builder.py         # K8s Job manifests (RFC 1123 compliant)
│   │   └── job_manager.py         # Job lifecycle, logs, and deletion
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── dag_scheduler.py       # DAG execution controller + telemetry hook
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── workflow.py            # Pydantic schemas (StageDefinition, etc.)
│   │
│   ├── profiling/
│   │   ├── __init__.py
│   │   ├── collector.py           # Container log telemetry parser
│   │   └── feature_builder.py     # 20-column RFC schema builder & filter
│   │
│   ├── prediction/                # Phase 3
│   │   ├── __init__.py
│   │   ├── feature_pipeline.py    # Feature extraction & encoding
│   │   ├── baseline.py            # Historical mean/median baselines
│   │   ├── runtime_model.py       # Runtime regressors (RF + XGBoost)
│   │   ├── resource_model.py      # CPU & Memory regressors
│   │   ├── confidence.py          # Variance & uncertainty scoring
│   │   └── drift.py               # Outlier & distribution shift detection
│   │
│   └── decision/                  # Phase 4
│       ├── __init__.py
│       └── decision_engine.py     # Resource sizing, SLA scheduler & fallback
│
├── workloads/
│   ├── Dockerfile                 # Alpine + bcftools + tabix + embedded chunks
│   └── simulate.py                # Real bcftools operations + telemetry emitter
│
├── workflows/
│   ├── linear.yaml                # Phase 1 linear pipeline
│   ├── parallel.yaml              # Phase 1 parallel diamond pipeline
│   ├── cyclic_invalid.yaml        # Validation test workflow
│   └── genomic_pipeline.yaml      # Phase 2 live genomic pipeline
│
├── data/
│   └── genomic/
│       ├── raw/                   # Immutable raw chr22 VCF (196 MB) + .tbi
│       ├── chunks/                # 9 VCF chunks (small, medium, large × 100s, 500s, full)
│       │   ├── metadata.json      # Real measured dimensions & variant counts
│       │   └── metadata.csv       # Tabular chunk metadata
│       └── samples/               # Deterministic sample ID lists (100, 500)
│
├── datasets/
│   ├── feature_schema.json        # Standardized 20-column RFC schema
│   ├── execution_history.csv      # Raw historical record (367 rows)
│   ├── genomic_execution_history.csv # Clean ML-ready dataset (94 rows)
│   └── genomic_dataset_summary.md # Statistical summary & ranges
│
├── models/                        # Phase 3 artifacts
│   ├── runtime/                   # Serialized runtime predictors
│   ├── cpu/                       # Serialized CPU predictors
│   ├── memory/                    # Serialized memory predictors
│   └── workers/                   # Serialized worker recommendations
│
├── k8s/
│   └── namespace.yaml             # cloudpilot namespace
│
├── tests/
│   ├── test_parser.py             # 11 tests
│   ├── test_validator.py          # 8 tests
│   ├── test_dag.py                # 10 tests
│   ├── test_job_builder.py        # 2 tests
│   ├── test_job_manager.py        # 4 tests
│   ├── test_scheduler.py          # 3 tests
│   ├── test_api.py                # 8 tests
│   ├── test_profiling.py          # 5 tests
│   └── test_prediction.py         # Phase 3 tests
│
├── scripts/
│   ├── setup_cluster.sh           # Linux cluster setup
│   ├── setup_cluster.ps1          # Windows cluster setup
│   ├── extract_genomic_chunks.py  # VCF regional & sample subset extraction
│   ├── build_dataset.py           # Workload execution matrix generator
│   ├── migrate_execution_history.py # 20-column schema migration
│   └── validate_execution_dataset.py # Quality, range & variation validator
│
├── docs/
│   └── phase2.md                  # Phase 2 reproducibility & architecture
├── requirements.txt
├── .gitignore
└── README.md
```

---

# PHASE 1 — Kubernetes Workflow Engine (COMPLETED)

## Status: ✅ Verified & Operational
- DAG parsing, dependency checking, cycle detection (NetworkX).
- Kubernetes Job manifests generated with RFC 1123 compliant names.
- Sequential and parallel execution validated on kind cluster.
- All 51 automated unit/integration tests passing.

---

# PHASE 2 — Genomic Workload Profiling & Monitoring (COMPLETED)

## Status: ✅ Verified & Operational

Phase 2 established real genomic processing and historical telemetry collection without hard-coded statistics.

### Completed Accomplishments:
1. **Raw Source**: Preserved compressed 1000 Genomes chr22 VCF (`data/genomic/raw/`, 196 MB) and index.
2. **Chunk Generation**: Created `scripts/extract_genomic_chunks.py` producing 9 deterministic combinations:
   - **3 Regions**: Small (100 kb / 1,170 variants), Medium (1 Mb / 17,985 variants), Large (4 Mb / 109,665 variants).
   - **3 Sample Sets**: 100 samples, 500 samples, 2,504 samples.
   - All indexed with `tabix -p vcf`.
3. **Containerized Workload**: Built `cloudpilot-workload:latest` with Alpine Linux, `bcftools 1.21`, and `tabix 1.21`. Container executes real VCF filtering, variant counts, and summary statistics, emitting standardized JSON profiling logs (`[CloudPilot Profiling]`).
4. **Standardized 20-Column Schema** (`datasets/feature_schema.json`):
   ```text
   workflow_id, stage_id, stage_type, workload_id, workload_source,
   chromosome, region_start, region_end, region_size, variant_count,
   sample_count, dataset_size_mb, requested_cpu, requested_memory_mb,
   worker_count, runtime_seconds, actual_cpu, actual_memory_mb, success, timestamp
   ```
5. **Separation of History**:
   - `datasets/execution_history.csv`: Complete raw audit trail (367 rows, including Phase 1 smoke tests and failure records).
   - `datasets/genomic_execution_history.csv`: 100% clean ML-ready dataset (94 rows, zero missing values, 0 duplicates, 100% successes).
6. **Verification Tooling**: `scripts/validate_execution_dataset.py` programmatically verifies multi-dimensional variation across region size, sample count, variant count, and runtime.

---

# PHASE 3 — Prediction & Intelligence

## Objective

Use the clean Phase 2 genomic execution dataset (`datasets/genomic_execution_history.csv`) to train machine learning models that predict workload requirements *before* execution.

CloudPilot will predict:

```text
1. runtime_seconds (continuous regression)
2. actual_cpu (continuous regression)
3. actual_memory_mb (continuous regression)
4. recommended worker_count (discrete optimization)
```

It will also calculate:

```text
5. prediction confidence (normalized uncertainty score in [0.0, 1.0])
6. distribution shift status (NORMAL, WARNING, SHIFTED)
```

---

## 3.1 Feature Pipeline & Encoding

Input features are extracted directly from the incoming stage definition and genomic metadata:

### Input Feature Vector ($X$):
- **Genomic Characteristics**:
  - `region_size` (integer: e.g. 100,000, 1,000,000, 4,000,000)
  - `variant_count` (integer: e.g. 1,170 to 109,665)
  - `sample_count` (integer: 100, 500, 2,504)
  - `dataset_size_mb` (float: 0.030 to 19.84 MB)
- **Workflow & Resource Characteristics**:
  - `stage_type` (categorical: `vcf_stats`, `filtering`, `variant_processing`, `feature_extraction`, `analysis` — one-hot encoded)
  - `worker_count` (integer: 1, 2, 4)
  - `requested_cpu_cores` (float: 0.25, 0.5, 1.0, 2.0 derived from `requested_cpu`)
  - `requested_memory_mb` (float: 256.0, 512.0, 1024.0, 2048.0)

Create:
```text
backend/prediction/
├── __init__.py
├── feature_pipeline.py     # Extracts and scales feature vectors
├── baseline.py             # Historical Mean/Median baselines
├── runtime_model.py        # Runtime prediction models
├── resource_model.py       # CPU & Memory prediction models
├── confidence.py           # Uncertainty & variance estimation
└── drift.py                # Outlier & distribution shift detection
```

---

## 3.2 Baseline Models

Before deploying complex algorithms, evaluate simple baselines to prove ML value:

1. **Global / Stage Mean Baseline**: Predicts the historical mean for the given `stage_type`.
2. **Stage Median Baseline**: Predicts the historical median for the given `stage_type`.
3. **Linear Regression / Ridge**: Standard regularized linear model.

The baseline establishes the error benchmark (MAE, RMSE) that ML models must beat.

---

## 3.3 Machine Learning Models

Train separate specialized regressors for each target:

1. **Random Forest Regressor** (`scikit-learn`):
   - Handles non-linear feature interactions between `variant_count` and `sample_count`.
   - Provides native tree variance for confidence scoring.
   - Robust against overfitting on medium-sized datasets.
2. **XGBoost Regressor** (`xgboost`):
   - Gradient boosted decision trees for peak predictive accuracy on tabular data.
   - Fast inference (<5ms per stage).

### Training Setup:
- Dataset: `datasets/genomic_execution_history.csv` (94 rows).
- Validation: 5-fold cross-validation or stratified train/test split (80/20).
- Hyperparameter tuning: `GridSearchCV` / `RandomizedSearchCV` across tree depth, estimator count, and learning rate.

---

## 3.4 Prediction Confidence Scoring

Predictions must not be treated as absolute truth; the decision engine requires an estimate of model certainty.

### Confidence Formulation:
Using the ensemble variance across the $T$ individual trees in Random Forest:
$$\bar{y}(x) = \frac{1}{T}\sum_{t=1}^{T} f_t(x), \quad \sigma^2(x) = \frac{1}{T}\sum_{t=1}^{T} (f_t(x) - \bar{y}(x))^2$$

The Coefficient of Variation ($\text{CV} = \frac{\sigma(x)}{\bar{y}(x)}$) measures relative disagreement. Confidence is mapped to $[0.0, 1.0]$:
$$\text{Confidence}(x) = \frac{1}{1 + \gamma \cdot \text{CV}(x)}$$
where $\gamma$ is a scaling factor tuned on validation residuals.

Expected Prediction Output:
```json
{
  "stage_id": "variant_processing_chr22_medium_500s",
  "predicted_runtime_seconds": 3.82,
  "predicted_actual_cpu": 0.65,
  "predicted_actual_memory_mb": 62.4,
  "recommended_worker_count": 2,
  "confidence": 0.91,
  "distribution_shift": "NORMAL"
}
```

---

## 3.5 Distribution Shift Detection

Detect when incoming workflow stages deviate from the training domain (e.g. unknown chromosome, unseen variant count >150k, sample size >3,000, or anomalous region size).

### Multi-Tier Shift Architecture:
1. **Domain Boundary Check**:
   Flag if any input parameter exceeds historical bounds $[X_{min}, X_{max}]$ by more than a safety margin (e.g. `region_size > 5,000,000` bp).
2. **Statistical Distance / Mahalanobis Distance**:
   Calculate distance $D_M(x) = \sqrt{(x - \mu)^T \Sigma^{-1} (x - \mu)}$ from the multivariate centroid of the training data.
3. **Shift Status Labels**:
   - `NORMAL`: Feature vector is comfortably inside the training distribution ($D_M \le \tau_1$).
   - `WARNING`: Feature vector is near the boundary or slightly extrapolated ($\tau_1 < D_M \le \tau_2$).
   - `SHIFTED`: Feature vector is an unseen outlier or out-of-distribution ($D_M > \tau_2$).

---

## 3.6 Model Evaluation & Artifacts

### Evaluation Metrics:
- **Runtime**: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE).
- **CPU & Memory**: MAE and peak residual error.
- **Comparison Table**: Baseline Mean vs. Ridge vs. Random Forest vs. XGBoost.

### Model Serialization:
Save fitted models and preprocessors using `joblib`:
```text
models/
├── runtime/model.joblib
├── cpu/model.joblib
├── memory/model.joblib
├── scaler.joblib
└── shift_detector.joblib
```

### Phase 3 Acceptance Criteria:
<<<<<<< HEAD
- [x] Clean genomic dataset loaded directly from `datasets/genomic_execution_history.csv`.
- [x] Baseline models implemented and evaluated.
- [x] Random Forest and XGBoost models trained for runtime, CPU, and memory.
- [x] ML models demonstrate superior MAE/RMSE over baselines.
- [x] Prediction confidence calculated using ensemble variance.
- [x] Distribution shift detector flags in-distribution vs out-of-distribution workloads.
- [x] Models serialized and reloadable via automated unit tests (`tests/test_prediction.py`).
=======
- [ ] Clean genomic dataset loaded directly from `datasets/genomic_execution_history.csv`.
- [ ] Baseline models implemented and evaluated.
- [ ] Random Forest and XGBoost models trained for runtime, CPU, and memory.
- [ ] ML models demonstrate superior MAE/RMSE over baselines.
- [ ] Prediction confidence calculated using ensemble variance.
- [ ] Distribution shift detector flags in-distribution vs out-of-distribution workloads.
- [ ] Models serialized and reloadable via automated unit tests (`tests/test_prediction.py`).
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

---

# PHASE 4 — Decision Engine & Intelligent Scheduling

## Objective

Connect Phase 3 predictions to the Kubernetes scheduling loop. The Decision Engine translates predictions, confidence scores, and SLA constraints into dynamic Kubernetes resource requests, limits, and thread allocations.

```text
Incoming Stage Definition (YAML)
               │
               ▼
   Extract Workload Metadata
  (region, variants, samples)
               │
               ▼
    Phase 3 Prediction Engine
  (runtime, CPU, RAM, confidence)
               │
               ▼
   Distribution Shift Detection
    (NORMAL, WARNING, SHIFTED)
               │
               ▼
   CloudPilot Decision Engine
 ├── Apply Safety Margins based on Confidence
 ├── Evaluate Deadline / SLA Budget
 └── Apply Conservative Fallback if SHIFTED
               │
               ▼
 Dynamic Kubernetes Job Manifest
  (cpu: requests/limits, mem: requests/limits, THREADS: env)
               │
               ▼
 Kubernetes Cluster Execution (kind)
```

---

## 4.1 Decision Logic & Sizing Formulas

Instead of static allocations (`1000m` CPU, `512Mi` RAM), the decision engine dynamically computes:

### 1. High Confidence & Normal Distribution (`confidence >= 0.80`, `shift == NORMAL`):
- Allocate tight, efficient resources with modest headroom (+25%):
  $$\text{Request}_{\text{cpu}} = \lceil \text{Predicted}_{\text{cpu}} \times 1.25 \rceil$$
  $$\text{Request}_{\text{mem}} = \lceil \text{Predicted}_{\text{mem}} \times 1.30 \rceil$$
  $$\text{Limit}_{\text{mem}} = \lceil \text{Request}_{\text{mem}} \times 1.50 \rceil$$

### 2. Moderate Confidence or Warning (`0.60 <= confidence < 0.80` or `shift == WARNING`):
- Widen headroom to prevent OOMKills and throttling (+60% to +75%):
  $$\text{Request}_{\text{cpu}} = \lceil \text{Predicted}_{\text{cpu}} \times 1.60 \rceil$$
  $$\text{Request}_{\text{mem}} = \lceil \text{Predicted}_{\text{mem}} \times 1.75 \rceil$$

### 3. Safe Fallback (`confidence < 0.60` or `shift == SHIFTED`):
- Bypass prediction and apply safe conservative profile:
  - `cpu`: `"2000m"`
  - `memory`: `"2Gi"`
  - `THREADS`: `4`
  - Record `fallback: true` in decision telemetry.

---

## 4.2 SLA & Deadline-Aware Scheduling

Given workflow deadline $D_{total}$ and remaining deadline $D_{rem}$:
1. Compute the critical path remaining runtime $T_{crit} = \sum_{\text{stages on critical path}} \text{Predicted}_{\text{runtime}}$.
2. If $T_{crit} > 0.80 \times D_{rem}$ (deadline pressure):
   - Proactively increase `worker_count` (e.g. from 1 to 2 or 4).
   - Scale CPU allocation proportionally to enable parallel execution inside `bcftools`.
3. If $T_{crit} \ll D_{rem}$ (relaxed deadline):
   - Maintain worker count at 1 or 2 to minimize cluster core footprint.

---

## 4.3 Kubernetes Integration

Update `backend/scheduler/dag_scheduler.py` and `backend/k8s/job_builder.py`:
- Job builder accepts dynamic `StageDefinition(cpu=decision.cpu, memory=decision.memory, env={"THREADS": decision.workers})`.
- Decision record logged to `datasets/execution_history.csv` to capture predicted vs actual efficiency.

### Phase 4 Acceptance Criteria:
<<<<<<< HEAD
- [x] Decision engine implemented under `backend/decision/decision_engine.py`.
- [x] Dynamic resource calculation applied to Kubernetes Job creation.
- [x] Safe fallback automatically triggers on low confidence or distribution shift.
- [x] SLA deadline constraint adjusts worker count and parallelism.
- [x] Zero OOMKills or container eviction failures across test suite.
=======
- [ ] Decision engine implemented under `backend/decision/decision_engine.py`.
- [ ] Dynamic resource calculation applied to Kubernetes Job creation.
- [ ] Safe fallback automatically triggers on low confidence or distribution shift.
- [ ] SLA deadline constraint adjusts worker count and parallelism.
- [ ] Zero OOMKills or container eviction failures across test suite.
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

---

# PHASE 5 — Dashboard, Integration & Evaluation

## Objective

Provide an intuitive web interface for workflow visualization and quantitatively evaluate CloudPilot against static Kubernetes allocation baselines.

---

## 5.1 CloudPilot Web Dashboard

Implemented as a lightweight web interface served directly by FastAPI (`backend/main.py`):

1. **Workflow Submission View**:
   - YAML workflow upload or template selector (`linear`, `parallel`, `genomic_pipeline`).
   - Genomic workload selector (small, medium, large × sample cohorts).
   - SLA deadline input field.
2. **Interactive DAG Graph**:
   - Visual dependency graph rendering nodes with state badges:
     - `PENDING` (gray), `RUNNING` (blue animation), `COMPLETED` (green), `FAILED` (red).
   - Hover cards showing predicted vs actual runtime, CPU, and memory.
3. **Telemetry & Intelligence Panel**:
   - Live metrics: Confidence score, Distribution Shift indicator (`NORMAL` / `SHIFTED`), Fallback trigger status.
   - Resource savings counter: Estimated core-hours and MB-hours saved compared to static provisioning.

---

## 5.2 Quantitative Evaluation Suite

Implement automated evaluation script `scripts/evaluate_platform.py` comparing three strategies across identical genomic workloads:

| Strategy | Description | Allocation Policy |
|---|---|---|
| **Baseline 1: Static Allocation** | Industry standard fixed sizing | Fixed `1000m` CPU, `1Gi` RAM for every stage |
| **Baseline 2: Unmanaged Kubernetes** | Default K8s burstable behavior | No requests/limits (competes for host resources) |
| **Baseline 3: CloudPilot Platform** | Intelligent predictive orchestration | Predicted actuals + confidence safety margins + SLA control |

### Evaluated Metrics:
1. **CPU Waste Ratio**: $\frac{\sum (\text{Allocated}_{\text{cpu}} - \text{Actual}_{\text{cpu}})}{\sum \text{Allocated}_{\text{cpu}}}$. (Target: >30% reduction).
2. **Memory Waste Ratio**: $\frac{\sum (\text{Allocated}_{\text{mem}} - \text{Actual}_{\text{mem}})}{\sum \text{Allocated}_{\text{mem}}}$. (Target: >35% reduction).
3. **SLA Violations**: Number of workflow runs exceeding deadline. (Target: 0% breaches).
4. **Prediction Accuracy**: Overall MAPE on runtime and memory.

---

# 6. Data Integrity & Git Safety Rules

- Never unzip the raw chr22 VCF (`ALL.chr22....genotypes.vcf.gz`).
- Always extract using indexed regional queries via `bcftools view -r ... -Oz` and `tabix -p vcf`.
- Maintain `.gitignore` to prevent committing raw or chunk VCF binaries:
  ```text
  data/genomic/raw/
  data/genomic/chunks/
  data/genomic/processed/
  *.vcf
  *.vcf.gz
  *.vcf.gz.tbi
  *.tar
  ```
- All code, metadata schemas, CSV datasets, and summary reports must remain tracked in Git.

---

# 7. Implementation Roadmap & Current Status

```text
PHASE 1: Kubernetes Workflow Engine        [ ✅ COMPLETED ]
   ├── YAML parser & DAG validator
   ├── Parallel branch scheduling
   └── Kubernetes Job execution

PHASE 2: Genomic Workload Profiling         [ ✅ COMPLETED ]
   ├── 9 VCF chunks (regions × samples)
   ├── Containerized bcftools workloads
   ├── 20-column standardized schema
   ├── execution_history.csv (367 rows)
   └── genomic_execution_history.csv (94 rows)

<<<<<<< HEAD
PHASE 3: Prediction & Intelligence          [ ✅ COMPLETED ]
=======
PHASE 3: Prediction & Intelligence          [ 🔄 NEXT STEP ]
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
   ├── Baseline predictors (Mean, Median, Ridge)
   ├── ML models (Random Forest, XGBoost)
   ├── Confidence scoring (ensemble variance)
   └── Distribution shift detection

<<<<<<< HEAD
PHASE 4: Decision Engine & Scheduling       [ ✅ COMPLETED ]
=======
PHASE 4: Decision Engine & Scheduling       [ 📋 PLANNED ]
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
   ├── Dynamic sizing with confidence headroom
   ├── SLA/deadline-aware worker allocation
   └── Safe fallback on distribution shift

<<<<<<< HEAD
PHASE 5: Dashboard, Integration & Eval      [ 🔄 NEXT STEP ]
=======
PHASE 5: Dashboard, Integration & Eval      [ 📋 PLANNED ]
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
   ├── Web dashboard with live DAG visualization
   ├── End-to-end feedback loop
   └── 3-way quantitative benchmarking
```

---

<<<<<<< HEAD
# 8. Immediate Next Steps (Starting Phase 5)

1. **Design FastAPI Dashboard UI**:
   Implement `backend/dashboard/` or integrate static HTML/JS directly with FastAPI in `backend/main.py`.
2. **Implement DAG Visualization**:
   Integrate Cytoscape.js or a similar library to render the running DAG and show node states (`PENDING`, `RUNNING`, `COMPLETED`).
3. **Connect Live Telemetry Panel**:
   Surface Phase 3/4 Intelligence (Confidence score, Fallback, Distribution shift) into the UI while workflows run.
4. **Build Evaluation Script**:
   Create `scripts/evaluate_platform.py` to run the 3-way quantitative benchmark (Static vs Unmanaged vs CloudPilot).
=======
# 8. Immediate Next Steps (Starting Phase 3)

1. **Install ML dependencies**:
   ```bash
   pip install scikit-learn xgboost joblib
   ```
2. **Create feature pipeline**:
   Create `backend/prediction/feature_pipeline.py` to load `datasets/genomic_execution_history.csv` and encode categorical/numeric features.
3. **Train baseline and ML models**:
   Implement `backend/prediction/baseline.py`, `backend/prediction/runtime_model.py`, and `backend/prediction/resource_model.py`.
4. **Implement confidence and shift scoring**:
   Implement `backend/prediction/confidence.py` and `backend/prediction/drift.py`.
5. **Add Phase 3 automated test suite**:
   Create `tests/test_prediction.py` verifying model training, persistence, and inference latency (<10ms).
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
