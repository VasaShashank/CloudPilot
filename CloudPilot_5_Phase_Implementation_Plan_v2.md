# CloudPilot — 5-Phase Implementation Plan
## Intelligent Predictive Resource Orchestration for Genomic Analysis Workflows on Kubernetes

> **Current dataset setup:** The 1000 Genomes Phase 3 chromosome 22 genotype VCF and its index are already downloaded and stored locally under:
>
> `data/genome/raw/`
>
> Keep the `.vcf.gz` compressed. **Do not unzip it.** The `.tbi` index is kept beside it for fast regional extraction with `bcftools`/`tabix`.

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

| Phase | Name | Main Outcome |
|---|---|---|
| 1 | Kubernetes Workflow Engine | A complete DAG can execute on Kubernetes |
| 2 | Genomic Workload Profiling & Monitoring | Real genomic workloads produce structured historical execution data |
| 3 | Prediction & Intelligence | CloudPilot predicts runtime/resources and evaluates confidence/shift |
| 4 | Decision Engine & Intelligent Scheduling | Predictions become Kubernetes resource/scheduling decisions |
| 5 | Dashboard, Integration & Evaluation | Complete CloudPilot system is demonstrated and evaluated |

---

# 3. Recommended Technology Stack

## Core

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- NetworkX
- PyYAML
- Kubernetes Python client
- Docker
- Kubernetes
- kind
- WSL2 + Ubuntu
- Git/GitHub

## Data and genomic processing

- VCF / VCF.GZ
- Tabix index (`.tbi`)
- bcftools
- tabix
- pandas
- NumPy

## Monitoring

- Kubernetes metrics
- Prometheus
- Prometheus Python client where required

## Machine Learning

- scikit-learn
- XGBoost
- joblib

## Frontend / visualization

- FastAPI backend
- Lightweight web dashboard
- Plotly/Chart.js or another simple visualization library if required

---

# 4. Current Project Structure

Use this structure as the project grows:

```text
cloudpilot/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   │
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   ├── validator.py
│   │   └── dag.py
│   │
│   ├── kubernetes/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── job_builder.py
│   │   └── job_manager.py
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── dag_scheduler.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── workflow.py
│   │
│   ├── profiling/
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   └── feature_builder.py
│   │
│   ├── prediction/
│   │   ├── __init__.py
│   │   ├── baseline.py
│   │   ├── runtime_model.py
│   │   ├── resource_model.py
│   │   ├── confidence.py
│   │   └── drift.py
│   │
│   └── decision/
│       ├── __init__.py
│       └── decision_engine.py
│
├── workloads/
│   ├── Dockerfile
│   └── simulate.py
│
├── workflows/
│   ├── linear.yaml
│   ├── parallel.yaml
│   └── cyclic_invalid.yaml
│
├── data/
│   └── genome/
│       ├── raw/
│       │   ├── ALL.chr22....genotypes.vcf.gz
│       │   └── ALL.chr22....genotypes.vcf.gz.tbi
│       │
│       ├── chunks/
│       │   ├── small/
│       │   ├── medium/
│       │   └── large/
│       │
│       └── processed/
│
├── datasets/
│   ├── execution_history.csv
│   └── feature_schema.json
│
├── models/
│   ├── runtime/
│   ├── cpu/
│   ├── memory/
│   └── workers/
│
├── k8s/
│   └── namespace.yaml
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_validator.py
│   ├── test_dag.py
│   ├── test_scheduler.py
│   ├── test_profiling.py
│   └── test_prediction.py
│
├── scripts/
│   ├── setup_cluster.sh
│   ├── setup_cluster.ps1
│   ├── extract_genomic_chunks.py
│   └── build_dataset.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

# PHASE 1 — Kubernetes Workflow Engine

## Objective

Build the reliable execution foundation of CloudPilot.

At the end of Phase 1:

> A YAML workflow DAG can be submitted, validated, converted into Kubernetes Jobs, executed in the correct dependency order, monitored, and completed successfully on a local kind cluster.

**No real genomic dataset is required for the core Phase 1 implementation.**

Use a simulated workload container first.

---

## 1.1 Workflow Definition

Create a YAML representation such as:

```yaml
workflow:
  id: linear-demo

stages:
  - id: qc
    type: qc
    depends_on: []

  - id: preprocessing
    type: preprocessing
    depends_on:
      - qc

  - id: alignment
    type: alignment
    depends_on:
      - preprocessing

  - id: analysis
    type: analysis
    depends_on:
      - alignment
```

Also create a parallel workflow:

```text
QC
 ↓
Preprocessing
 ├── Alignment
 └── Feature Extraction
        ↓
      Analysis
```

And an intentionally invalid cyclic workflow:

```text
A → B → C → A
```

---

## 1.2 Parser

Implement:

```text
backend/workflow/parser.py
```

Responsibilities:

- Read YAML.
- Parse workflow ID.
- Parse stage definitions.
- Parse dependencies.
- Convert YAML into typed Python objects.
- Reject malformed workflow definitions.

Main interface:

```python
parse_workflow(yaml_path_or_string)
```

---

## 1.3 Validator

Implement:

```text
backend/workflow/validator.py
```

Validate:

- workflow ID exists
- stage IDs are unique
- dependency references exist
- at least one stage exists
- no invalid dependency declarations
- no cycles

Invalid workflows must be rejected before Kubernetes Jobs are created.

---

## 1.4 DAG Representation

Implement:

```text
backend/workflow/dag.py
```

Create `WorkflowDAG`.

Required operations:

```python
get_root_stages()
get_runnable_stages(completed_set)
get_downstream(stage_id)
get_dependencies(stage_id)
topological_order()
get_parallel_groups()
```

The DAG should support:

- linear workflows
- branching workflows
- parallel stages
- converging dependencies
- cycle detection

---

## 1.5 Kubernetes Integration

Implement:

```text
backend/kubernetes/client.py
backend/kubernetes/job_builder.py
backend/kubernetes/job_manager.py
```

Use:

- `BatchV1Api`
- `CoreV1Api`

CloudPilot namespace:

```text
cloudpilot
```

Each workflow stage becomes a Kubernetes Job.

Example naming:

```text
cloudpilot-{workflow_id}-{stage_id}
```

Use labels:

```text
cloudpilot/workflow=<workflow-id>
cloudpilot/stage=<stage-id>
app=cloudpilot
```

---

## 1.6 Simulated Workload

Create:

```text
workloads/Dockerfile
workloads/simulate.py
```

The simulator should:

- receive `STAGE_NAME`
- receive `STAGE_TYPE`
- perform light computation
- sleep for a configurable duration
- print useful execution logs
- exit successfully

This lets Phase 1 test orchestration without requiring genomic processing.

---

## 1.7 DAG Scheduler

Implement:

```text
backend/scheduler/dag_scheduler.py
```

Responsibilities:

1. Validate workflow.
2. Build DAG.
3. Find root stages.
4. Submit runnable stages.
5. Poll Job status.
6. Detect completion.
7. Unlock downstream stages.
8. Run independent branches in parallel.
9. Stop/fail appropriately if a required stage fails.
10. Record workflow/stage state.

---

## 1.8 State Models

Create models such as:

```text
StageDefinition
WorkflowDefinition

StageState
WorkflowState

StageStatus
WorkflowStatus
```

Example statuses:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
SKIPPED
```

---

## 1.9 API

FastAPI endpoints:

```text
POST /workflows
GET  /workflows
GET  /workflows/{id}
POST /workflows/{id}/run
GET  /workflows/{id}/stages/{stage_id}/logs
```

---

## 1.10 Phase 1 Verification

Run:

```bash
pytest tests/ -v
```

Then:

```bash
kind create cluster --name cloudpilot
docker build -t cloudpilot-workload:latest ./workloads/
kind load docker-image cloudpilot-workload:latest
kubectl apply -f k8s/namespace.yaml
```

Run the API:

```bash
python main.py serve
```

Run a workflow:

```bash
python main.py run workflows/linear.yaml
```

Verify:

```bash
kubectl get jobs -n cloudpilot
kubectl get pods -n cloudpilot
```

Test all three:

```text
linear.yaml
parallel.yaml
cyclic_invalid.yaml
```

### Phase 1 completion criteria

- Linear DAG executes successfully.
- Parallel branches execute concurrently.
- Downstream stages wait for dependencies.
- Cyclic workflow is rejected.
- Kubernetes Job failures are detected.
- Logs can be retrieved.
- Automated tests pass.

---

# PHASE 2 — Genomic Workload Profiling & Monitoring

## Objective

Introduce the real genomic workload and create the historical execution dataset required for prediction.

The 1000 Genomes Phase 3 chr22 dataset is already available locally.

Current location:

```text
data/genome/raw/
```

Expected files:

```text
data/genome/raw/
├── ALL.chr22....genotypes.vcf.gz
└── ALL.chr22....genotypes.vcf.gz.tbi
```

## IMPORTANT

**Do not unzip the `.vcf.gz` file.**

The compressed VCF can be queried directly using its `.tbi` index.

The original raw dataset should remain untouched.

---

## 2.1 Genomic Chunk Generation

Create:

```text
scripts/extract_genomic_chunks.py
```

Use:

- `bcftools`
- `tabix`

Create controlled workload sizes.

Initial example:

```text
Small:
22:1000000-1100000
100 kb

Medium:
22:1000000-2000000
1 Mb

Large:
22:1000000-5000000
4 Mb
```

The exact ranges can be adjusted after inspecting the number of variants.

Store outputs under:

```text
data/genome/chunks/
├── small/
├── medium/
└── large/
```

Each extracted VCF should also be indexed.

Example:

```bash
bcftools view \
  -r 22:1000000-2000000 \
  data/genome/raw/ALL.chr22....vcf.gz \
  -Oz \
  -o data/genome/chunks/medium/chr22_1mb.vcf.gz

tabix -p vcf data/genome/chunks/medium/chr22_1mb.vcf.gz
```

---

## 2.2 Do Not Treat Chunk Size as the Only Feature

CloudPilot should eventually capture several workload characteristics:

### Dataset characteristics

- genomic region size
- number of variants
- number of samples
- VCF compressed size
- VCF uncompressed/processed size where measurable
- population subset
- chromosome/region
- workload type

### Workflow characteristics

- stage type
- dependency count
- parallel branches
- worker count
- requested CPU
- requested memory

---

## 2.3 Genomic Workload Container

Extend the workload image so that selected workflow stages can process actual VCF chunks.

Example workload types:

```text
vcf_stats
filtering
variant_processing
aggregation
analysis
```

Start with lightweight operations.

Do not build an unnecessarily complicated bioinformatics pipeline yet.

The goal is to generate repeatable computational workloads that can be profiled.

---

## 2.4 Workload Profiling

Collect for every stage execution:

```text
workflow_id
stage_id
stage_type

dataset_size
region_size
variant_count
sample_count

requested_cpu
requested_memory
worker_count

start_time
end_time
runtime

actual_cpu_usage
actual_memory_usage

success
failure
```

Derived:

```text
CPU utilization
Memory utilization
Resource waste
Runtime error
Deadline compliance
```

---

## 2.5 Historical Execution Dataset

Create:

```text
datasets/execution_history.csv
```

Each row should represent a stage execution.

Example conceptual schema:

```text
workflow_id
stage_id
stage_type
region_size
variant_count
sample_count
dataset_size_mb
requested_cpu
requested_memory_mb
worker_count
runtime_seconds
actual_cpu
actual_memory_mb
success
timestamp
```

This becomes the training/evaluation dataset for Phase 3.

---

## 2.6 Monitoring

Integrate Kubernetes/Prometheus metrics after basic profiling works.

Collect:

- CPU usage
- memory usage
- Job start/end times
- pod status
- resource requests
- resource limits

Avoid adding Prometheus complexity before the basic execution/profile pipeline works.

### Phase 2 completion criteria

- Raw chr22 VCF remains compressed and indexed.
- Small/medium/large genomic chunks can be generated.
- Genomic workloads execute through CloudPilot.
- Runtime and resource measurements are recorded.
- Historical execution dataset is generated.
- Monitoring data can be associated with individual workflow stages.

---

# PHASE 3 — Prediction & Intelligence

## Objective

Use the historical execution data to predict workload requirements before execution.

CloudPilot should predict:

```text
runtime
CPU requirement
memory requirement
worker count
```

It should also estimate:

```text
prediction confidence
distribution shift
```

---

## 3.1 Feature Engineering

Input features can include:

```text
dataset size
region size
variant count
sample count
stage type
workflow position
dependency count
worker count
historical runtime statistics
```

Create:

```text
backend/prediction/
```

---

## 3.2 Baseline Models

Start simple.

Examples:

- historical mean
- historical median
- moving average
- linear regression

The baseline establishes whether machine learning actually improves prediction.

---

## 3.3 Machine Learning Models

Then evaluate:

- Random Forest
- Gradient Boosting
- XGBoost

Use separate models where appropriate for:

```text
runtime
CPU
memory
workers
```

Do not assume XGBoost is automatically necessary. Compare it against simpler baselines.

---

## 3.4 Prediction Confidence

The prediction system should produce:

```text
prediction
confidence
```

Example:

```json
{
  "predicted_runtime": 42.5,
  "predicted_cpu": 1.8,
  "predicted_memory_mb": 1450,
  "confidence": 0.87
}
```

Confidence should be based on measurable model uncertainty/error behavior rather than a manually invented score.

---

## 3.5 Distribution Shift Detection

Detect when the incoming workload differs materially from historical training data.

Potential inputs:

```text
dataset size
variant count
sample count
region characteristics
stage type
resource profile
```

Start with simple statistical distance/outlier methods before implementing sophisticated drift detection.

Example output:

```text
NORMAL
WARNING
SHIFTED
```

The label should represent a measurable rule/model output.

---

## 3.6 Model Evaluation

Track:

### Runtime

- MAE
- RMSE
- MAPE where appropriate

### Resource prediction

- CPU prediction error
- memory prediction error
- worker prediction accuracy

### Operational impact

- resource waste
- over-provisioning
- under-provisioning
- deadline/SLA compliance

---

## 3.7 Model Artifacts

Store trained models under:

```text
models/
├── runtime/
├── cpu/
├── memory/
└── workers/
```

Use `joblib` or an appropriate model serialization method.

### Phase 3 completion criteria

- Historical dataset is usable for training.
- Baseline predictions work.
- ML predictions work.
- Runtime/resource predictions are measurable.
- Confidence is calculated.
- Distribution shift can be detected.
- Models are saved and reloadable.
- Evaluation metrics are produced.

---

# PHASE 4 — Decision Engine & Intelligent Scheduling

## Objective

Turn predictions into actual Kubernetes resource and scheduling decisions.

This is the core intelligence layer of CloudPilot.

---

## 4.1 Decision Inputs

The decision engine receives:

```text
workflow DAG
stage information
genomic workload characteristics

predicted runtime
predicted CPU
predicted memory
predicted worker count

prediction confidence
distribution shift

deadline / SLA
available Kubernetes resources
```

---

## 4.2 Decision Output

Example:

```json
{
  "cpu": "2",
  "memory": "2Gi",
  "workers": 2,
  "parallelism": 2,
  "confidence": 0.87,
  "fallback": false
}
```

---

## 4.3 Resource Allocation Logic

Basic decision flow:

```text
New stage
   ↓
Extract workload features
   ↓
Generate predictions
   ↓
Check confidence
   ↓
Check distribution shift
   ↓
Check deadline/SLA
   ↓
Determine CPU/RAM/workers
   ↓
Submit Kubernetes workload
```

---

## 4.4 Safe Fallback

If:

```text
confidence is low
OR
distribution shift is high
OR
prediction unavailable
```

CloudPilot should use a safe fallback strategy.

Possible fallback:

```text
historical conservative allocation
or
configured default resource profile
```

The fallback should be explicitly recorded.

---

## 4.5 SLA-Aware Scheduling

The decision engine should consider:

```text
predicted runtime
remaining workflow time
deadline
available resources
parallelism
```

The objective is not simply:

> "Use the least CPU."

It should balance:

```text
deadline compliance
resource efficiency
prediction confidence
```

---

## 4.6 Dynamic Kubernetes Allocation

Integrate decisions with the Kubernetes Job builder.

Instead of always using fixed resources:

```yaml
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
```

CloudPilot should generate resource settings from the decision engine.

---

## 4.7 Scheduling Scenarios

Test:

### Scenario A — Normal workload

Prediction trusted.

### Scenario B — Large workload

Higher predicted resource requirements.

### Scenario C — Distribution-shifted workload

Prediction becomes less trusted and fallback activates.

### Scenario D — Tight deadline

Scheduler allocates resources/parallelism to meet the SLA where possible.

### Scenario E — Resource-constrained cluster

Scheduler must operate within available cluster capacity.

### Phase 4 completion criteria

- Predictions influence Kubernetes resources.
- Confidence influences decisions.
- Distribution shift influences decisions.
- Fallback works.
- SLA/deadline information affects scheduling.
- Dynamic resource allocation can be demonstrated.

---

# PHASE 5 — Dashboard, Integration & Evaluation

## Objective

Combine all components into a demonstrable CloudPilot platform and quantitatively evaluate its benefits.

---

## 5.1 Dashboard

Provide:

### Workflow submission

- upload/select workflow YAML
- submit workflow
- select genomic workload

### DAG view

Show:

```text
QC → Preprocessing → Alignment → Analysis
```

including parallel branches.

### Live execution

Show:

- pending
- running
- succeeded
- failed

### Prediction view

Show:

```text
Predicted runtime
Actual runtime

Predicted CPU
Actual CPU

Predicted memory
Actual memory
```

### Decision view

Show:

```text
Predicted resources
Selected resources
Confidence
Distribution shift
Fallback
SLA/deadline
```

---

## 5.2 End-to-End Flow

The final CloudPilot flow should be:

```text
User
  ↓
Dashboard
  ↓
Workflow YAML
  ↓
DAG Parser + Validator
  ↓
Workload Profiler
  ↓
Prediction Engine
  ↓
Confidence + Shift Detection
  ↓
Decision Engine
  ↓
Kubernetes Scheduler
  ↓
Kubernetes Jobs
  ↓
Prometheus / Execution Metrics
  ↓
Historical Dataset
  ↓
Future Model Training
```

This creates the intended feedback loop:

```text
Execution
   ↓
Monitoring
   ↓
Historical Data
   ↓
Learning
   ↓
Better Predictions
   ↓
Better Decisions
   ↓
Better Execution
```

---

# 6. Evaluation Plan

CloudPilot should be compared against multiple baselines.

## Baseline 1 — Static Allocation

Use fixed CPU/memory settings for every workload.

## Baseline 2 — Default Kubernetes Behavior

Run workloads without CloudPilot's prediction-driven resource decisions.

## Baseline 3 — CloudPilot

Use:

```text
prediction
+
confidence
+
distribution shift
+
SLA-aware decision making
```

---

## 6.1 Evaluation Metrics

### Performance

- workflow completion time
- stage runtime
- throughput

### Resource efficiency

- CPU utilization
- memory utilization
- CPU waste
- memory waste
- over-provisioning

### Prediction quality

- runtime MAE
- runtime RMSE
- CPU prediction error
- memory prediction error
- worker prediction accuracy

### Scheduling quality

- deadline compliance
- SLA compliance
- fallback frequency
- scheduling decision latency

### Robustness

Evaluate:

```text
normal workloads
larger workloads
unseen workload sizes
distribution-shifted workloads
resource-constrained workloads
```

---

# 7. Genomic Dataset Strategy

## Source Dataset

Use:

```text
1000 Genomes Project Phase 3
```

Initial working source:

```text
Chromosome 22 genotype VCF
```

The downloaded raw file is stored under:

```text
data/genome/raw/
```

with its `.tbi` index.

## Why chromosome 22?

Chromosome 22 is being used as a practical development source because its Phase 3 VCF is much smaller than the largest chromosome files while still representing an autosomal 1000 Genomes workload.

The chromosome itself is **not** the learning target.

The important workload features are:

```text
region size
variant count
sample count
dataset size
stage type
processing characteristics
```

Later, additional chromosomes/regions can be introduced to test generalization and distribution shift.

---

# 8. Dataset Chunking Strategy

Do not create separate downloaded raw files for every workload.

Maintain:

```text
data/genome/raw/
```

as the source.

Generate workload chunks:

```text
data/genome/chunks/
```

Example:

```text
small/
  chr22_100kb.vcf.gz
  chr22_100kb.vcf.gz.tbi

medium/
  chr22_1mb.vcf.gz
  chr22_1mb.vcf.gz.tbi

large/
  chr22_4mb.vcf.gz
  chr22_4mb.vcf.gz.tbi
```

This allows reproducible workload generation.

---

# 9. Data Integrity Rules

Never modify the raw VCF.

Use:

```text
raw → extraction → chunks → processing → execution
```

not:

```text
raw → manually modify raw file
```

Keep large genomic files out of Git.

`.gitignore` should include:

```text
data/genome/raw/
data/genome/chunks/
data/genome/processed/
*.vcf
*.vcf.gz
*.vcf.gz.tbi
```

---

# 10. Recommended Installation Order

## Already required for Phase 1

```text
WSL2
Ubuntu
Docker Desktop
kubectl
kind
Python 3.11+
Git
VS Code
```

## Phase 1 Python packages

```text
fastapi
uvicorn
networkx
pyyaml
kubernetes
pydantic
pytest
```

## Phase 2

Install:

```text
bcftools
tabix
pandas
numpy
```

Ubuntu:

```bash
sudo apt update
sudo apt install -y bcftools tabix
```

## Phase 3

Install:

```text
scikit-learn
xgboost
joblib
```

## Later only if required

```text
Prometheus
Grafana
```

Do not install heavy tools such as TensorFlow, PyTorch, CUDA, Kafka, Redis, Airflow, or Kubeflow unless a later implementation decision genuinely requires them.

---

# 11. Implementation Order

Follow this exact high-level order:

```text
PHASE 1
Kubernetes DAG execution
        ↓
PHASE 2
Genomic workload + profiling
        ↓
PHASE 3
Prediction + confidence + shift detection
        ↓
PHASE 4
Decision engine + intelligent scheduling
        ↓
PHASE 5
Dashboard + evaluation
```

Do **not** jump directly to machine learning.

CloudPilot needs reliable execution data before prediction can be meaningful.

---

# 12. Definition of Done

## Phase 1

A YAML DAG executes correctly on Kubernetes.

## Phase 2

Real genomic workloads execute and produce structured profiling data.

## Phase 3

CloudPilot predicts runtime/resources and reports confidence and shift.

## Phase 4

Predictions influence Kubernetes resource and scheduling decisions.

## Phase 5

The complete platform is demonstrable and quantitatively evaluated against baselines.

---

# 13. Final Project Architecture

```text
                    ┌──────────────────────┐
                    │      Dashboard       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Workflow API / DAG   │
                    │ Parser + Validator   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Workload Profiler    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Prediction Engine    │
                    │ Runtime / CPU / RAM  │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    ▼                      ▼
             Confidence              Shift Detection
                    │                      │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Decision Engine     │
                    │ SLA + Resources      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Kubernetes Scheduler │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Kubernetes Jobs      │
                    │ Genomic Workloads    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Monitoring / Metrics │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Historical Dataset   │
                    └──────────┬───────────┘
                               │
                               └──────► Model Improvement
```

---

# 14. Immediate Next Steps

Since the raw chr22 files are already downloaded:

### Step 1

Verify:

```text
data/genome/raw/
├── chr22 VCF.GZ
└── chr22 VCF.GZ.TBI
```

### Step 2

Do **not** unzip the VCF.

### Step 3

Finish Phase 1 Kubernetes workflow execution first.

### Step 4

Install `bcftools` and `tabix` when starting Phase 2.

### Step 5

Extract the first small genomic chunk.

### Step 6

Run that chunk through a CloudPilot workload.

### Step 7

Start collecting execution records.

### Step 8

Generate enough historical runs for Phase 3 prediction.

---

## Core principle

CloudPilot is not simply a Kubernetes workflow runner and not simply a genomic ML model.

Its main contribution is the complete loop:

```text
Genomic workload
      ↓
Profile
      ↓
Predict
      ↓
Estimate confidence
      ↓
Detect shift
      ↓
Make resource decision
      ↓
Schedule on Kubernetes
      ↓
Measure actual execution
      ↓
Learn from execution history
```

That loop should remain the central architecture throughout the project.
