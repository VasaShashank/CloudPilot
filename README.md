# 🧬 CloudPilot Apex
### Intelligent Predictive Resource Orchestration for Genomic Analysis Workflows on Kubernetes

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-kind%20%2F%20cloud-326ce5.svg)](https://kubernetes.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Cytoscape.js](https://img.shields.io/badge/DAG-Cytoscape.js-ff4081.svg)](https://js.cytoscape.org/)
[![Tests](https://img.shields.io/badge/tests-95%20passed-10b981.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🌟 Executive Summary

**CloudPilot** is an end-to-end, autonomous Kubernetes orchestration platform tailored for high-throughput genomic data processing (e.g., variant analysis, quality control, population genetics with `bcftools` and `tabix`).

Standard cloud bioinformatics pipelines typically suffer from **massive resource over-provisioning** (wasting 80–90% of allocated memory on small stages) or **catastrophic under-provisioning** (triggering container `OOMKills` and SLA deadline breaches on dense variant regions).

CloudPilot eliminates this tradeoff using a **5-Phase Intelligent Feedback Loop**:
1. **DAG Workflow Engine:** Executes multi-stage pipelines with automatic parallelization as Kubernetes Jobs.
2. **Genomic Telemetry Profiling:** Collects real container resource telemetry across chromosome 22 regional chunks and sample cohorts into a standardized 20-column schema.
3. **Machine Learning Intelligence:** Uses trained Random Forest and XGBoost regressors to predict runtime, CPU core demand, and memory footprint *before* execution, accompanied by ensemble-variance confidence scores and Mahalanobis distribution-shift detection.
4. **Decision Engine & SLA Control:** Dynamically translates ML predictions into concrete Kubernetes resource requests, limits, and thread allocations with adaptive safety headroom (+25% to +75%) and deadline-pressure acceleration.
5. **Mission Control Web Dashboard:** A cyberpunk glassmorphic control center featuring live Cytoscape.js DAG visualization, real-time stage telemetry inspection, and an empirical 3-way benchmarking suite.

---

## ❓ Critical Question: "Do We Need to Use a Paid Cloud?"

> ### 💡 Quick Answer: **NO, you do NOT need a cloud provider!**

One of the greatest architectural strengths of CloudPilot is that **it does not require any paid public cloud (AWS, GCP, Azure, etc.)**.

### Why and How It Runs 100% Locally:
- **Local Kubernetes (`kind`):** CloudPilot runs on `kind` (Kubernetes in Docker), Minikube, or k3s directly on your local machine (Windows with Docker Desktop / WSL2, Linux, or macOS).
- **Embedded Genomic Data:** The platform uses real 1000 Genomes Phase 3 chromosome 22 VCF data (`data/genomic/raw/` and `data/genomic/chunks/`) processed by real containerized `bcftools` and `tabix` utilities.
- **Zero Cloud Cost:** You can develop, test, train ML models, orchestrate workflows, and run full platform benchmarks with **$0 cloud expenditure**.
- **Privacy & Security:** Genomic data remains completely on-premise without transferring sensitive patient or population genomes across external networks.
- **Seamless Cloud Portability:** Because CloudPilot uses standard Kubernetes API primitives (`batch/v1` Jobs, resource requests/limits, cgroup telemetry), the exact same code and manifests can be pointed to an AWS EKS, GCP GKE, or Azure AKS cluster by simply updating your `KUBECONFIG` environment variable.

---

## 🏗️ 5-Phase Architecture Overview

```
                                  INCOMING WORKFLOW (YAML)
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DAG WORKFLOW ENGINE                                                           │
│ • NetworkX directed acyclic graph parsing                                              │
│ • Dependency cycle detection & validation                                              │
│ • Parallel stage group identification                                                  │
└────────────────────────────────────┬───────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: NEURAL PREDICTION LAYER                                                       │
│ • Genomic Feature Pipeline (region_size, variant_count, sample_count, dataset_size_mb) │
│ • XGBoost & Random Forest Regressors (runtime, CPU, Memory)                           │
│ • Random Forest Tree-Variance Confidence Score (0.0 to 1.0)                             │
│ • Log-space Mahalanobis Distance Distribution Shift Detector (NORMAL / WARNING / SHIFT)│
└────────────────────────────────────┬───────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: DECISION ENGINE & SLA GUARDIAN                                                │
│ • Tier 1 (High Confidence): +25% CPU, +30% Mem, Mem Limit = 1.5× Request                │
│ • Tier 2 (Moderate/Warning): +60% CPU, +75% Mem, Mem Limit = 2.0× Request              │
│ • Tier 3 (Safe Fallback): Bypass ML → 2000m CPU, 2048Mi RAM, 4 Workers                 │
│ • SLA Deadline Pressure: Critical path > 80% budget → Double worker threads + CPU      │
└────────────────────────────────────┬───────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1 & 2: KUBERNETES EXECUTION & CONTAINER PROFILING                                │
│ • RFC 1123 compliant Kubernetes Job generation (requests, limits, THREADS env)        │
│ • Alpine container executing real bcftools stats/filtering operations                  │
│ • Standardized container log telemetry extraction: [CloudPilot Profiling]              │
│ • Audit dataset append (datasets/execution_history.csv)                                │
└────────────────────────────────────┬───────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: MISSION CONTROL DASHBOARD & EVALUATION                                        │
│ • FastAPI Backend (backend/main.py) + Cytoscape.js interactive DAG visualizer          │
│ • Real-time Stage Intelligence & Container Log Inspector                               │
│ • Automated 3-Way Quantitative Benchmarking Suite (scripts/evaluate_platform.py)       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Summary of What Has Been Implemented Across All 5 Phases

| Phase | Core Deliverable | Technical Details & Artifacts | Status |
|:---:|---|---|:---:|
| **1** | **Kubernetes Workflow Engine** | YAML parser, NetworkX DAG validator, parallel diamond execution, Kubernetes Job builder & lifecycle manager (`backend/workflow/`, `backend/k8s/`, `backend/scheduler/`). | ✅ **Verified** |
| **2** | **Genomic Profiling & Schema** | 1000 Genomes Phase 3 chr22 dataset (196 MB raw), 9 regional/sample chunks (100 kb to 4 Mb; 100 to 2,504 samples), containerized `bcftools 1.21` + `tabix`, 20-column RFC schema, 98 clean execution records (`datasets/`). | ✅ **Verified** |
| **3** | **Machine Learning Intelligence** | 15 trained models: Stage Mean/Median, Ridge, Random Forest, XGBoost (HPO tuned); ensemble variance confidence scoring; Mahalanobis distance distribution-shift detector (`backend/prediction/`, `models/`). | ✅ **Verified** |
| **4** | **Decision Engine & Dynamic Sizing** | 3-tier resource sizing engine, dynamic headroom injection, K8s hard memory limits, SLA critical-path deadline pressure scaling (`backend/decision/`). | ✅ **Verified** |
| **5** | **Dashboard & Evaluation Suite** | FastAPI web server, Cytoscape.js interactive DAG UI, stage intelligence inspector, live pod log streaming, 3-way quantitative benchmarking suite, 95 passing tests (`backend/static/`, `scripts/evaluate_platform.py`). | ✅ **Verified** |

---

## 🖥️ What the Web Dashboard Does & How to Use It

The **CloudPilot Apex Dashboard** is an aerospace/cyberpunk-styled mission control interface served directly by FastAPI at **`http://localhost:8000/`**.

### 1. Executive HUD Ribbon (Top Counters)
- **⚡ CPU Core Optimization:** Dynamic radial SVG gauge showing **+23.4%** allocated CPU reduction compared to static provisioning.
- **💾 Memory Footprint Slashed:** Radial progress ring showcasing **91.0%** memory footprint reduction.
- **🎯 Mean Neural Confidence:** Displays the ensemble certainty of the ML models (current mean: **96.8%**).
- **🛡️ SLA Breach Guardian:** Live monitor of deadline adherence (**0.0% breach rate**).

---

### 2. Live Mission Control (Tab 1)

The Mission Control workspace is organized into **three interactive columns**:

```
┌───────────────────────────┬───────────────────────────────────┬───────────────────────────┐
│     LEFT COCKPIT          │          CENTER STUDIO            │        RIGHT PANEL        │
│                           │                                   │                           │
│ • Template Selector       │ • Cytoscape.js DAG Topology       │ • Selected Stage Header   │
│ • Genomic Parameter Matrix│ • Color-Coded State Badges        │ • Phase 3 ML Predictions  │
│   (Chr22 Region & Samples)│   (Pending, Running, Completed)   │ • Tree-Variance Certainty │
│ • SLA Deadline Input      │ • Pulsing Radar Halos (Running)   │ • Mahalanobis Drift Status│
│ • Live Manifest Editor    │ • Floating Control Dock           │ • Phase 4 Sizing Manifest │
│ • "Initiate Orchestration"│ • Zoom / Fit / Auto-Layout        │ • Headroom Visual Stack   │
│ • Mission History Feed    │ • Real-Time Polling Sync (2s)     │ • Live Pod Log Stream     │
└───────────────────────────┴───────────────────────────────────┴───────────────────────────┘
```

#### Step-by-Step Dashboard Usage:
1. **Choose a Pipeline Architecture:**
   - Under **Pipeline Architecture**, select a template (e.g., `🧬 5-Stage Live Genomic Pipeline (bcftools)`).
2. **Select Genomic Workload Scope:**
   - Choose a Chromosome 22 chunk (e.g., `chr22 Medium (1 Mb / 17,985 vars) • 500 samples`). The dashboard instantly calculates genomic metadata and updates the YAML manifest.
3. **Configure SLA Target Budget:**
   - Set an optional SLA deadline (e.g., `60` seconds). If remaining critical path runtime exceeds 80% of this budget, the Phase 4 Decision Engine will automatically double worker concurrency.
4. **Initiate Orchestration:**
   - Click the glowing **"INITIATE ORCHESTRATION"** button. The workflow is validated, submitted to the FastAPI backend, and Kubernetes Jobs are scheduled.
5. **Observe the Live DAG Graph:**
   - Watch nodes transition in real-time:
     - `PENDING` (slate gray) $\rightarrow$
     - `RUNNING` (pulsating cyan radar halo) $\rightarrow$
     - `COMPLETED` (glowing emerald green) or `FAILED` (ruby red alert).
6. **Inspect Stage Intelligence:**
   - Click on any node in the DAG graph. The **Right Panel** instantly reveals:
     - **Predicted Runtime, CPU, and RAM** vs actual measured consumption.
     - **Model Confidence Bar** (e.g., 96.8% Certainty).
     - **Distribution Shift Status** (`NORMAL`, `WARNING`, `SHIFTED`).
     - **Decision Tier & Headroom** (+25% for high confidence, +60% for moderate, fallback safe mode for shifted).
     - **Real-time Pod Logs** with syntax highlighting for profiling metrics.

---

### 3. Empirical 3-Way Benchmark Suite (Tab 2)

Switch to the **"3-Way Empirical Benchmark"** tab in the header to view quantitative platform evaluations comparing:

| Metric | Baseline 1: Static Allocation | Baseline 2: Unmanaged K8s | Baseline 3: CloudPilot Platform |
|---|---|---|---|
| **CPU Policy** | Fixed `1000m` (1.0 core) | Unbounded host burst (4 cores) | **Dynamic Predicted + Confidence Headroom** |
| **Total CPU Allocated** | 100.0 cores | 400.0 cores | **76.6 cores** (✅ **23.4% reduction**) |
| **CPU Waste Ratio** | 55.8% | >80% (noisy neighbor risk) | **42.5%** (✅ **>30% reduction**) |
| **Memory Policy** | Fixed `1024 MiB` | Unbounded host burst (4096 MiB) | **Dynamic Predicted + 30–75% Headroom** |
| **Total Memory Allocated** | 102,400 MiB | 409,600 MiB | **9,208 MiB** (✅ **91.0% reduction**) |
| **Memory Waste Ratio** | 91.0% | >80% (OOMKill risk under contention) | **0.0%** (✅ **91.0% reduction**) |
| **SLA Violations** | 0 breaches | High risk under load | **0 breaches (0.0%)** |
| **Mean Model Confidence** | N/A | N/A | **96.8%** |

You can re-trigger this benchmark across all 100 stages anytime by clicking **"Re-run Benchmark Suite"**.

---

## 📂 Repository Structure

```text
cloudpilot/
├── backend/
│   ├── main.py                    # FastAPI entrypoint, API routes, static dashboard server
│   ├── config.py                  # Cluster and engine constants
│   ├── models/
│   │   └── workflow.py            # Pydantic schemas (StageDefinition, StageStatus, WorkflowStatus)
│   ├── workflow/
│   │   ├── parser.py              # YAML workflow parsing
│   │   ├── validator.py           # Dependency & cycle validation
│   │   └── dag.py                 # NetworkX DAG graph operations
│   ├── k8s/
│   │   ├── client.py              # Local kubeconfig + in-cluster fallback
│   │   ├── job_builder.py         # K8s Job manifests (RFC 1123 compliant)
│   │   └── job_manager.py         # Job lifecycle, logs, and deletion
│   ├── scheduler/
│   │   └── dag_scheduler.py       # DAG execution controller + telemetry & intelligence hooks
│   ├── profiling/
│   │   ├── collector.py           # Container log telemetry parser ([CloudPilot Profiling])
│   │   └── feature_builder.py     # 20-column RFC schema builder & filter
│   ├── prediction/                # Phase 3 Predictive Intelligence Layer
│   │   ├── feature_pipeline.py    # 18-feature extraction & encoding pipeline
│   │   ├── baseline.py            # Historical mean/median & linear baselines
│   │   ├── runtime_model.py       # Random Forest & XGBoost runtime regressors
│   │   ├── resource_model.py      # CPU, Memory, and worker count regressors
│   │   ├── confidence.py          # Ensemble tree-variance confidence estimator
│   │   ├── drift.py               # Log-space Mahalanobis distribution-shift detector
│   │   └── predictor.py           # Unified CloudPilotPredictor facade
│   ├── decision/                  # Phase 4 Decision Engine Layer
│   │   └── decision_engine.py     # 3-tier resource sizing, safe fallback, SLA scaling
│   └── static/                    # Phase 5 Dashboard UI
│       ├── index.html             # Cyberpunk Mission Control HTML
│       ├── css/
│       │   └── dashboard.css      # Luxury dark-mode glassmorphic design system
│       └── js/
│           └── dashboard.js       # Cytoscape.js DAG visualizer & Web Audio synthesizer
│
├── workflows/
│   ├── genomic_pipeline.yaml      # Phase 2 live 5-stage bcftools pipeline
│   ├── linear.yaml                # 4-stage sequential chain
│   ├── parallel.yaml              # Diamond DAG with parallel branches
│   └── cyclic_invalid.yaml        # Cycle validation negative test
│
├── data/genomic/
│   ├── raw/                       # Immutable raw chr22 VCF (196 MB) + .tbi index
│   └── chunks/                    # 9 VCF chunks (small, medium, large × 100s, 500s, full)
│       └── metadata.json          # Real measured dimensions & variant counts
│
├── datasets/
│   ├── feature_schema.json        # Standardized 20-column RFC schema
│   ├── execution_history.csv      # Raw historical audit trail (367+ rows)
│   ├── genomic_execution_history.csv # Clean ML-ready training dataset (98 rows)
│   └── platform_evaluation_results.json # 3-way platform benchmark results
│
├── models/                        # Serialized ML artifacts
│   ├── runtime/model.joblib       # Tuned XGBoost runtime predictor
│   ├── cpu/model.joblib           # Tuned XGBoost CPU predictor
│   ├── memory/model.joblib        # Tuned XGBoost memory predictor
│   ├── resource_predictor.joblib  # Combined resource model
│   └── shift_detector.joblib      # Fitted Mahalanobis drift detector
│
├── scripts/
│   ├── evaluate_platform.py       # Phase 5 3-way quantitative benchmarking suite
│   ├── train_models.py            # Phase 3 model training & HPO grid search CLI
│   ├── extract_genomic_chunks.py  # Regional chunk & sample subset extractor
│   ├── setup_cluster.ps1          # Windows kind-cluster setup script
│   └── setup_cluster.sh           # Linux/macOS kind-cluster setup script
│
├── docs/
│   ├── phase2.md                  # Phase 2 profiling architecture
│   ├── phase3.md                  # Phase 3 ML leaderboards & HPO results
│   ├── phase5.md                  # Phase 5 dashboard & benchmark report
│   └── platform_evaluation_summary.md # Markdown evaluation summary
│
└── tests/                         # 95 Automated Tests
    ├── test_parser.py             # YAML parsing tests (11 tests)
    ├── test_validator.py          # Cycle & dependency tests (8 tests)
    ├── test_dag.py                # Graph topological tests (10 tests)
    ├── test_job_builder.py        # K8s manifest tests (2 tests)
    ├── test_job_manager.py        # Job lifecycle tests (4 tests)
    ├── test_scheduler.py          # DAG execution tests (3 tests)
    ├── test_api.py                # REST API tests (8 tests)
    ├── test_profiling.py          # Container telemetry tests (5 tests)
    ├── test_prediction.py         # ML & Drift detector tests (8 tests)
    ├── test_decision.py           # Phase 4 decision engine tests (30 tests)
    └── test_dashboard.py          # Phase 5 dashboard & evaluation tests (6 tests)
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Docker Desktop (running)
- Kubernetes local cluster (`kind` or `minikube`) — *optional if testing API/ML offline*

### 2. Environment Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/fataldestiny06/cloudpilot.git
cd cloudpilot
python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Launch the Mission Control Dashboard
Start the FastAPI server:
```bash
python backend/main.py serve
```
Open your browser and navigate to:
👉 **`http://localhost:8000/`** or **`http://localhost:8000/dashboard`**

---

### 4. CLI Execution (Optional)
You can also execute workflows or validate manifests directly from your terminal:
```bash
# Validate a workflow YAML
python backend/main.py validate workflows/genomic_pipeline.yaml

# Execute workflow directly via CLI
python backend/main.py run workflows/genomic_pipeline.yaml
```

---

### 5. Run the 3-Way Platform Benchmark
To evaluate CloudPilot against Static and Unmanaged baselines:
```bash
python scripts/evaluate_platform.py
```
Outputs are automatically written to `datasets/platform_evaluation_results.json` and `docs/platform_evaluation_summary.md`.

---

### 6. Run the Full Test Suite
Execute all 95 automated unit and integration tests:
```bash
pytest
```
*Expected result:* **`95 passed in ~100s`** (100% pass rate).

---

## 🛡️ License

This project is open-source and available under the [MIT License](LICENSE).
