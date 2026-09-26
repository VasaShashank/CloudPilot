# CloudPilot — Phase 2: Genomic Workload Profiling & Monitoring

## 1. Overview

Phase 2 enhances the CloudPilot platform by integrating **real genomic data execution**, controlled regional/sample workload generation, containerized bioinformatics processing via `bcftools`, automated metric telemetry extraction, and complete execution dataset separation.

The objective of Phase 2 is to produce a clean, reproducible, and sufficiently varied genomic execution dataset that Phase 3 ML models can directly consume for runtime, CPU, and memory prediction.

```text
Raw chr22 VCF (1000 Genomes)
          │
          ▼
scripts/extract_genomic_chunks.py
  ├── 3 Genomic Regions (100kb, 1Mb, 4Mb)
  └── 3 Sample Cohorts (100, 500, 2504 samples)
          │
          ▼
9 BGZ-compressed & Tabix-indexed VCF Chunks
  (data/genomic/chunks/small, medium, large)
          │
          ▼
Workload Container (workloads/simulate.py)
  ├── Real bcftools stats, view, query processing
  └── Emits [CloudPilot Profiling] JSON Telemetry
          │
          ▼
Kubernetes DAG Execution (backend/scheduler/dag_scheduler.py)
          │
          ▼
Metric Collection (backend/profiling/collector.py)
          ├── datasets/execution_history.csv (Raw History: 353 rows)
          └── datasets/genomic_execution_history.csv (Clean ML Dataset: 90 rows)
```

---

## 2. Directory Structure

```text
cloudpilot/
├── data/
│   └── genomic/
│       ├── raw/
│       │   ├── ALL.chr22....genotypes.vcf.gz         # Immutable raw source VCF (196 MB)
│       │   └── ALL.chr22....genotypes.vcf.gz.tbi     # Tabix index
│       └── chunks/
│           ├── small/                                # 100kb chunks (100s, 500s, full)
│           ├── medium/                               # 1Mb chunks (100s, 500s, full)
│           ├── large/                                # 4Mb chunks (100s, 500s, full)
│           ├── metadata.json                         # Real chunk dimensions & variant counts
│           └── metadata.csv                          # CSV metadata
├── backend/
│   └── profiling/
│       ├── collector.py                              # Telemetry parser & collector
│       └── feature_builder.py                        # 20-column schema builder & dataset filter
├── workloads/
│   ├── Dockerfile                                    # Workload image with bcftools & tabix
│   └── simulate.py                                   # Genomic processing & telemetry emitter
├── datasets/
│   ├── feature_schema.json                           # 20-column JSON schema
│   ├── execution_history.csv                         # Raw history (353 rows)
│   ├── genomic_execution_history.csv                 # Clean genomic ML dataset (90 rows)
│   └── genomic_dataset_summary.md                    # Statistical summary & verification
└── scripts/
    ├── extract_genomic_chunks.py                     # Deterministic chunk generation script
    ├── build_dataset.py                              # Workload matrix generator
    └── validate_execution_dataset.py                 # Dataset quality & variation validator
```

---

## 3. End-to-End Reproducibility Workflow

### Step 1: Extract Genomic Chunks and Sample Subsets
Extract the 9 controlled workload combinations from the raw chr22 VCF using `bcftools` and `tabix`:
```bash
python scripts/extract_genomic_chunks.py
```
This produces:
- `data/genomic/chunks/small/chr22_small_{100s,500s,full}.vcf.gz`
- `data/genomic/chunks/medium/chr22_medium_{100s,500s,full}.vcf.gz`
- `data/genomic/chunks/large/chr22_large_{100s,500s,full}.vcf.gz`
- `data/genomic/chunks/metadata.json` and `metadata.csv`

### Step 2: Build and Load Workload Image into Kind
```bash
# Build container image
docker build -t cloudpilot-workload:latest workloads/

# Import image into kind cluster
docker save cloudpilot-workload:latest -o workloads/workload.tar
docker cp workloads/workload.tar cloudpilot-control-plane:/root/workload.tar
docker exec cloudpilot-control-plane ctr --namespace=k8s.io images import /root/workload.tar
rm workloads/workload.tar
docker exec cloudpilot-control-plane rm /root/workload.tar
```

### Step 3: Run Live Genomic Workflows
Execute genomic pipelines on Kubernetes:
```bash
python backend/main.py run workflows/genomic_pipeline.yaml
```

### Step 4: Populate Workload Execution Matrix
Generate the balanced matrix across all 9 chunks, 5 stages, and diverse resource configurations:
```bash
python scripts/build_dataset.py
```

### Step 5: Validate Dataset Quality
Execute the automated dataset verification tool:
```bash
python scripts/validate_execution_dataset.py
```

---

## 4. Dataset Schema

The standardized 20-column schema (`datasets/feature_schema.json`) captures:

| Column | Type | Description |
|---|---|---|
| `workflow_id` | string | Unique workflow run identifier |
| `stage_id` | string | Stage name (e.g. `vcf_stats_chr22_small_100s`) |
| `stage_type` | string | Bioinformatics operation type |
| `workload_id` | string | Genomic chunk identifier |
| `workload_source` | string | `genomic`, `simulated`, or `phase1_test` |
| `chromosome` | string | Target chromosome (`22`) |
| `region_start` | integer | Genomic coordinate start (e.g. `16050000`) |
| `region_end` | integer | Genomic coordinate end (e.g. `16150000`, `17050000`, `20050000`) |
| `region_size` | integer | Span in base pairs (`100000`, `1000000`, `4000000`) |
| `variant_count` | integer | Measured variant count (`1170`, `17985`, `109665`) |
| `sample_count` | integer | Number of samples processed (`100`, `500`, `2504`) |
| `dataset_size_mb` | float | Compressed input size in MB |
| `requested_cpu` | string | K8s CPU request (`250m` – `2000m`) |
| `requested_memory_mb` | float | K8s Memory request in MB (`256.0` – `2048.0`) |
| `worker_count` | integer | Worker threads (`1`, `2`, `4`) |
| `runtime_seconds` | float | Execution duration |
| `actual_cpu` | float | Monitored CPU core usage |
| `actual_memory_mb` | float | Monitored peak RSS memory in MB |
| `success` | boolean | Completion status (`True`/`False`) |
| `timestamp` | string | ISO-8601 execution timestamp |

---

## 5. Verification & Tests

To run the complete test suite:
```bash
pytest tests/ -v
```
All unit and integration tests for Phase 1 DAG execution, parser, validator, job builder/manager, and Phase 2 profiling/telemetry collection must pass with 100% success.
