# CloudPilot — Phase 1: Kubernetes Workflow Execution Engine

**CloudPilot** is an Intelligent Predictive Resource Orchestration Platform for Genomic Analysis Workflows on Kubernetes.

**Phase 1** implements the foundational workflow execution engine: a DAG-based orchestrator that parses YAML workflow definitions, validates dependencies, detects parallelism, and executes stages as Kubernetes Jobs with proper dependency management.

---

## 1. Project Purpose

Phase 1 proves the core concept:

```
YAML DAG → Dependency Validation → Parallel Execution → Kubernetes Jobs → Status Reporting
```

**What Phase 1 does:**
- Parses workflow DAGs from YAML definitions
- Validates structure and detects cycles
- Identifies stages that can run in parallel
- Creates Kubernetes Jobs for each stage
- Monitors Job completion and unlocks dependent stages
- Reports per-stage and workflow-level status

**What Phase 1 does NOT do (reserved for later phases):**
- ML-powered resource prediction
- Dynamic autoscaling
- Prometheus monitoring
- Authentication/authorization
- Production cloud deployment

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CloudPilot Backend                     │
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐ │
│  │   FastAPI    │───▶│  Workflow    │───▶│  Scheduler   │ │
│  │   API / CLI  │    │  Parser +   │    │  (DAG        │ │
│  │             │    │  Validator + │    │  Execution   │ │
│  │             │    │  DAG Builder │    │  Controller) │ │
│  └─────────────┘    └─────────────┘    └──────┬───────┘ │
│                                               │         │
│                                        ┌──────▼───────┐ │
│                                        │  K8s Layer   │ │
│                                        │  (Job Builder│ │
│                                        │  + Manager)  │ │
│                                        └──────┬───────┘ │
└───────────────────────────────────────────────┼─────────┘
                                                │
                                    ┌───────────▼──────────┐
                                    │   Kubernetes Cluster  │
                                    │   (kind / Minikube)   │
                                    │                       │
                                    │  ┌─────┐  ┌────────┐ │
                                    │  │ Job │  │  Job   │ │
                                    │  │ (qc)│  │(align) │ │
                                    │  └─────┘  └────────┘ │
                                    └───────────────────────┘
```

### Project Structure

```
cloudpilot/
├── backend/
│   ├── main.py                    # FastAPI + CLI entrypoint
│   ├── config.py                  # Configuration constants
│   ├── models/
│   │   └── workflow.py            # Pydantic models (StageDefinition, WorkflowStatus, etc.)
│   ├── workflow/
│   │   ├── parser.py              # YAML parsing
│   │   ├── validator.py           # Structural validation
│   │   └── dag.py                 # NetworkX DAG operations
│   ├── k8s/
│   │   ├── client.py              # K8s client helpers
│   │   ├── job_builder.py         # Build Job manifests
│   │   └── job_manager.py         # Create/monitor/delete Jobs
│   └── scheduler/
│       └── dag_scheduler.py       # DAG execution controller
├── workloads/
│   ├── simulate.py                # Simulated genomic workload
│   └── Dockerfile
├── workflows/
│   ├── linear.yaml                # Linear 4-stage pipeline
│   ├── parallel.yaml              # Diamond with parallel branches
│   └── cyclic_invalid.yaml        # Invalid cyclic graph (test)
├── k8s/
│   └── namespace.yaml
├── tests/
│   ├── test_parser.py             # 11 test cases
│   ├── test_validator.py          # 8 test cases
│   └── test_dag.py                # 10 test cases
├── scripts/
│   ├── setup_cluster.sh           # Linux/macOS setup
│   └── setup_cluster.ps1          # Windows setup
├── requirements.txt
└── README.md
```

---

## 3. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Docker | 20.10+ | Build workload images |
| kind | 0.20+ | Local Kubernetes cluster |
| kubectl | 1.28+ | Cluster interaction |

### Install Prerequisites (Windows)

```powershell
# Python: https://python.org/downloads
# Docker Desktop: https://docker.com/products/docker-desktop
# kind
choco install kind
# kubectl
choco install kubernetes-cli
```

### Install Prerequisites (Linux/macOS)

```bash
# kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/kubectl
```

---

## 4. Installation

```bash
cd cloudpilot

# Create virtual environment (recommended)
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 5. Kubernetes Cluster Setup

### Using kind (recommended)

#### Automated Setup

**Windows (PowerShell):**
```powershell
.\scripts\setup_cluster.ps1
```

**Linux/macOS:**
```bash
chmod +x scripts/setup_cluster.sh
./scripts/setup_cluster.sh
```

#### Manual Setup

```bash
# 1. Create cluster
kind create cluster --name cloudpilot

# 2. Verify cluster
kubectl cluster-info --context kind-cloudpilot

# 3. Apply namespace
kubectl apply -f k8s/namespace.yaml

# 4. Verify namespace
kubectl get namespace cloudpilot
```

### Using Minikube (alternative)

```bash
minikube start --profile cloudpilot
kubectl apply -f k8s/namespace.yaml
```

---

## 6. Building Docker Images

### For kind

```bash
# Build the workload image
docker build -t cloudpilot-workload:latest ./workloads/

# Load into kind cluster
kind load docker-image cloudpilot-workload:latest --name cloudpilot
```

### For Minikube

```bash
# Point Docker to Minikube's daemon
eval $(minikube docker-env --profile cloudpilot)

# Build directly inside Minikube
docker build -t cloudpilot-workload:latest ./workloads/
```

---

## 7. Running the Backend

### API Server

```bash
cd cloudpilot
python backend/main.py serve
```

Server starts at `http://localhost:8000`.

### API Documentation

FastAPI auto-generates interactive docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 8. Submitting a Workflow

### Option A: CLI (Direct Execution)

```bash
# Validate a workflow (no K8s needed)
python backend/main.py validate workflows/linear.yaml

# Run a workflow (requires K8s cluster)
python backend/main.py run workflows/parallel.yaml
```

### Option B: REST API

```bash
# 1. Submit workflow
curl -X POST http://localhost:8000/workflows \
  -F "file=@workflows/parallel.yaml"

# Response: {"workflow_id": "a1b2c3d4", "status": {...}}

# 2. Start execution
curl -X POST http://localhost:8000/workflows/a1b2c3d4/run

# 3. Check status
curl http://localhost:8000/workflows/a1b2c3d4

# 4. List all workflows
curl http://localhost:8000/workflows

# 5. Get stage logs
curl http://localhost:8000/workflows/a1b2c3d4/stages/qc/logs
```

### Option C: Submit via Raw YAML Body

```bash
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"yaml_body": "workflow:\n  name: test\nstages:\n  - id: qc\n    type: quality_control"}'
```

---

## 9. Monitoring Jobs

### kubectl commands

```bash
# Watch Jobs in the cloudpilot namespace
kubectl get jobs -n cloudpilot --watch

# List all pods
kubectl get pods -n cloudpilot

# View logs for a specific stage
kubectl logs job/cloudpilot-a1b2c3d4-qc -n cloudpilot

# Describe a job for debugging
kubectl describe job cloudpilot-a1b2c3d4-qc -n cloudpilot

# Delete all Jobs (cleanup)
kubectl delete jobs -n cloudpilot --all
```

### Job Naming Convention

Jobs follow the pattern: `cloudpilot-{workflow_id}-{stage_id}`

Example: `cloudpilot-a1b2c3d4-alignment`

### Labels

All Jobs are tagged with:
- `app: cloudpilot`
- `cloudpilot/workflow: {workflow_id}`
- `cloudpilot/stage: {stage_id}`

---

## 10. Testing

### Unit Tests (no K8s required)

```bash
cd cloudpilot
python -m pytest tests/ -v
```

**Test coverage:**

| Test File | Tests | What's Covered |
|-----------|-------|----------------|
| `test_parser.py` | 11 | YAML parsing, error handling, optional fields |
| `test_validator.py` | 8 | Duplicate IDs, missing deps, empty stages, self-deps |
| `test_dag.py` | 10 | Cycles, topological order, parallel groups, runnable stages |
| **Total** | **29** | |

### Integration Tests (requires K8s)

```bash
# 1. Setup cluster + build image (see Section 5-6)

# 2. Test linear workflow
python backend/main.py run workflows/linear.yaml

# 3. Test parallel workflow
python backend/main.py run workflows/parallel.yaml

# 4. Test cyclic rejection
python backend/main.py validate workflows/cyclic_invalid.yaml
# Expected: Error about cycle detection

# 5. Verify Jobs ran correctly
kubectl get jobs -n cloudpilot
kubectl get pods -n cloudpilot

# 6. Check logs
kubectl logs job/cloudpilot-<id>-qc -n cloudpilot
```

---

## 11. Example Workflows

### Linear Pipeline

```yaml
# workflows/linear.yaml
workflow:
  name: genomic-linear

stages:
  - id: qc
    type: quality_control
  - id: preprocessing
    type: preprocessing
    depends_on: [qc]
  - id: alignment
    type: alignment
    depends_on: [preprocessing]
  - id: analysis
    type: analysis
    depends_on: [alignment]
```

**Execution flow:** `QC → Preprocessing → Alignment → Analysis` (strictly sequential)

### Parallel Diamond Pipeline

```yaml
# workflows/parallel.yaml
workflow:
  name: genomic-parallel

stages:
  - id: qc
    type: quality_control
  - id: preprocessing
    type: preprocessing
    depends_on: [qc]
  - id: alignment
    type: alignment
    depends_on: [preprocessing]
  - id: feature_extraction
    type: feature_extraction
    depends_on: [preprocessing]
  - id: analysis
    type: analysis
    depends_on: [alignment, feature_extraction]
```

**Execution flow:**
```
QC → Preprocessing → [Alignment ∥ Feature Extraction] → Analysis
```

After Preprocessing completes, Alignment and Feature Extraction run **concurrently**.

---

## 12. Expected Behavior

### Workflow Validation (`validate` command)

```
$ python backend/main.py validate workflows/parallel.yaml

Workflow 'genomic-parallel' is valid
Stages: ['qc', 'preprocessing', 'alignment', 'feature_extraction', 'analysis']
Topological order: ['qc', 'preprocessing', 'alignment', 'feature_extraction', 'analysis']
Parallel groups: [['qc'], ['preprocessing'], ['alignment', 'feature_extraction'], ['analysis']]
```

### Cyclic Rejection

```
$ python backend/main.py validate workflows/cyclic_invalid.yaml

ERROR [CloudPilot] Validation failed: Cycle detected in workflow dependencies:
[('stage_a', 'stage_b'), ('stage_b', 'stage_c'), ('stage_c', 'stage_a')]
```

### Workflow Execution (with K8s cluster)

```
[CloudPilot] Workflow submitted: genomic-parallel (id: a1b2c3d4)
[CloudPilot] Parsed 5 stages
[CloudPilot] DAG validation successful
[CloudPilot] Topological order: ['qc', 'preprocessing', 'alignment', 'feature_extraction', 'analysis']
[CloudPilot] Parallel groups: [['qc'], ['preprocessing'], ['alignment', 'feature_extraction'], ['analysis']]
[CloudPilot] Runnable stages: ['qc']
[CloudPilot] Created Job: cloudpilot-a1b2c3d4-qc
[CloudPilot] Stage completed: qc
[CloudPilot] Runnable stages: ['preprocessing']
[CloudPilot] Created Job: cloudpilot-a1b2c3d4-preprocessing
[CloudPilot] Stage completed: preprocessing
[CloudPilot] Runnable stages: ['alignment', 'feature_extraction']
[CloudPilot] Created Job: cloudpilot-a1b2c3d4-alignment
[CloudPilot] Created Job: cloudpilot-a1b2c3d4-feature_extraction
[CloudPilot] Stage completed: alignment
[CloudPilot] Stage completed: feature_extraction
[CloudPilot] Runnable stages: ['analysis']
[CloudPilot] Created Job: cloudpilot-a1b2c3d4-analysis
[CloudPilot] Stage completed: analysis
[CloudPilot] Workflow COMPLETED successfully
```

### Status API Response

```json
{
  "workflow_id": "a1b2c3d4",
  "name": "genomic-parallel",
  "state": "COMPLETED",
  "stages": {
    "qc": {"id": "qc", "type": "quality_control", "state": "COMPLETED", "job_name": "cloudpilot-a1b2c3d4-qc"},
    "preprocessing": {"id": "preprocessing", "type": "preprocessing", "state": "COMPLETED"},
    "alignment": {"id": "alignment", "type": "alignment", "state": "COMPLETED"},
    "feature_extraction": {"id": "feature_extraction", "type": "feature_extraction", "state": "COMPLETED"},
    "analysis": {"id": "analysis", "type": "analysis", "state": "COMPLETED"}
  }
}
```

---

## 13. Known Limitations

| Limitation | Reason | Future Phase |
|------------|--------|--------------|
| In-memory workflow storage | Phase 1 simplicity | Phase 2+ (database) |
| No authentication | Out of scope | Phase 3+ |
| No resource prediction | Requires ML models | Phase 2 |
| No auto-scaling | Requires Prometheus + ML | Phase 3 |
| Simulated workloads only | Proving orchestration, not genomics | Phase 2+ |
| Polling-based monitoring | Simple and reliable | Phase 2 (events/watches) |
| Single Docker image for all stages | Sufficient for simulation | Phase 2+ (per-stage images) |
| No persistent storage between stages | Phase 1 doesn't need data handoff | Phase 2 (PVCs) |

---

## Quick Reference

```bash
# Validate workflow (no K8s needed)
python backend/main.py validate workflows/parallel.yaml

# Run workflow (K8s required)
python backend/main.py run workflows/linear.yaml

# Start API server
python backend/main.py serve

# Run unit tests
python -m pytest tests/ -v

# Setup cluster (Windows)
.\scripts\setup_cluster.ps1

# Setup cluster (Linux/macOS)
./scripts/setup_cluster.sh

# Watch Jobs
kubectl get jobs -n cloudpilot --watch

# Cleanup
kubectl delete jobs -n cloudpilot --all
```
