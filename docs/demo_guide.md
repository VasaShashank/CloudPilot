# CloudPilot demonstration guide

## 1. Prepare the local environment

```powershell
python -m pip install -r requirements.txt
.\scripts\setup_cluster.ps1
```

The setup script builds the workload image from the repository root, imports it
into the `kind-cloudpilot` cluster, and applies the `cloudpilot` namespace.

For a real genomic demonstration, place the indexed chr22 VCF and its `.tbi`
index under `data/genomic/raw/`, then run:

```powershell
python scripts/extract_genomic_chunks.py
.\scripts\setup_cluster.ps1
```

The raw VCF and generated chunks remain intentionally untracked. Without them,
the Phase 1 workflow still runs using the workload container's simulation path.

## 2. Demonstrate the five phases

```powershell
# Phase 1: validate and execute a parallel DAG
python backend/main.py validate workflows/parallel.yaml
python backend/main.py run workflows/parallel.yaml
kubectl get jobs,pods -n cloudpilot

# Phase 2: verify the telemetry data; with chunks present, execute real bcftools work
python scripts/validate_execution_dataset.py
python backend/main.py run workflows/genomic_pipeline.yaml

# Phase 3: train and inspect predictive intelligence
python scripts/train_models.py
python backend/main.py predict workflows/genomic_pipeline.yaml

# Phase 4: observe dynamic decision records after a workflow run
Get-Content datasets/decision_history.jsonl -Tail 5

# Phase 5: run the dashboard and evaluation suite
python backend/main.py serve
# Open http://localhost:8000/dashboard
python scripts/evaluate_platform.py

# Automated verification
pytest -q
```

## 3. Dashboard walkthrough

1. Open `http://localhost:8000/dashboard`.
2. Select **Parallel** to demonstrate DAG dependencies, or **Genomic Pipeline** for genomic stages.
3. Set a deadline, submit the workflow, and watch node states move from PENDING to RUNNING to COMPLETED.
4. Select a node to show prediction confidence, shift status, dynamic CPU/memory decision, telemetry, and pod logs.
5. Open the evaluation tab to compare static, unmanaged, and CloudPilot allocation replay metrics.
