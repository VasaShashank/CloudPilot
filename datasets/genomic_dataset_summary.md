# CloudPilot — Phase 2 Genomic Execution Dataset Summary

## Overview

This document provides human-readable summary metrics and reproducibility evidence for the Phase 2 genomic execution dataset generated for **CloudPilot** (*An Intelligent Predictive Resource Orchestration Platform for Genomic Analysis Workflows on Kubernetes*).

The dataset is partitioned into:
- **Raw History** (`datasets/execution_history.csv`): Complete historical record (353 rows) including Phase 1 smoke tests, simulated workflows, failures, and genomic runs.
- **Clean Genomic Dataset** (`datasets/genomic_execution_history.csv`): Filtered, high-integrity dataset (90 rows) formatted specifically for Phase 3 ML predictive model training.

---

## Source Genomic Data & Extraction Methodology

### Source VCF
- **Source Dataset**: 1000 Genomes Project Phase 3 Release
- **Chromosome**: Chromosome 22
- **File**: `data/genomic/raw/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz` (196 MB)
- **Index**: `data/genomic/raw/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz.tbi`
- **Integrity**: Source VCF remained fully compressed and unaltered throughout extraction.

### Extraction Methodology
Extracting regional chunks and deterministic sample subsets using `bcftools` and `tabix` via `scripts/extract_genomic_chunks.py`:
1. **Region Extraction**:
   - `small`: `chr22:16050000-16150000` (100 kb)
   - `medium`: `chr22:16050000-17050000` (1,000 kb / 1 Mb)
   - `large`: `chr22:16050000-20050000` (4,000 kb / 4 Mb)
2. **Sample Subsetting**:
   - `100s`: First 100 deterministic sample IDs from the 1000 Genomes cohort
   - `500s`: First 500 deterministic sample IDs
   - `full`: All 2,504 samples
3. **Chunk Outputs**:
   All 9 chunks are compressed with `bgzip` and indexed with `tabix -p vcf`:
   - `chr22_small_100s.vcf.gz` (100 kb, 1,170 variants, 100 samples, 0.030 MB)
   - `chr22_small_500s.vcf.gz` (100 kb, 1,170 variants, 500 samples, 0.058 MB)
   - `chr22_small_full.vcf.gz` (100 kb, 1,170 variants, 2,504 samples, 0.170 MB)
   - `chr22_medium_100s.vcf.gz` (1 Mb, 17,985 variants, 100 samples, 0.423 MB)
   - `chr22_medium_500s.vcf.gz` (1 Mb, 17,985 variants, 500 samples, 0.898 MB)
   - `chr22_medium_full.vcf.gz` (1 Mb, 17,985 variants, 2,504 samples, 2.966 MB)
   - `chr22_large_100s.vcf.gz` (4 Mb, 109,665 variants, 100 samples, 2.676 MB)
   - `chr22_large_500s.vcf.gz` (4 Mb, 109,665 variants, 500 samples, 5.805 MB)
   - `chr22_large_full.vcf.gz` (4 Mb, 109,665 variants, 2,504 samples, 19.836 MB)

---

## Clean Genomic Dataset Statistics (`datasets/genomic_execution_history.csv`)

| Metric | Measured Value |
|---|---|
| **Total Executions** | 90 |
| **Successful Executions** | 90 (100%) |
| **Failed Executions** | 0 |
| **Stage Types Represented** | 5 (`vcf_stats`, `filtering`, `variant_processing`, `feature_extraction`, `analysis`) |
| **Genomic Region Sizes** | 3 levels: `100,000` (100 kb), `1,000,000` (1 Mb), `4,000,000` (4 Mb) |
| **Sample Count Tiers** | 3 levels: `100`, `500`, `2,504` samples |
| **Variant Count Range** | 3 levels: `1,170`, `17,985`, `109,665` variants |
| **Dataset Compressed Size** | `0.0301 MB` to `19.8364 MB` |
| **Requested CPU Allocations** | `250m`, `500m`, `1000m`, `2000m` |
| **Requested Memory Allocations** | `256Mi`, `512Mi`, `1Gi`, `2Gi` (256.0 MB – 2048.0 MB) |
| **Worker Threads** | `1`, `2`, `4` threads |
| **Runtime Range** | `0.370s` to `25.117s` (Mean: `2.446s`) |
| **Actual CPU Usage** | `0.250` to `1.700` cores (Mean: `0.604`) |
| **Actual Memory Usage** | `28.00 MB` to `278.58 MB` (Mean: `77.56 MB`) |
| **Timestamp Range** | `2026-09-20 14:09:26` to `2026-09-23 13:39:26` |
| **Missing / Null Values** | 0 (0.0%) |
| **Duplicate Tuples** | 0 (0.0%) |

---

## Raw Execution History Summary (`datasets/execution_history.csv`)

| Metric | Measured Value |
|---|---|
| **Total Executions** | 353 |
| **Workload Sources** | `genomic` (90), `simulated` (242), `phase1_test` (21) |
| **Successful Executions** | 349 (98.9%) |
| **Failed Executions** | 4 (1.1%) (retained for negative sampling and error profiling) |
| **Missing / Null Values** | 0 (0.0%) |
| **Total Columns** | 20 (standardized RFC schema) |

---

## Reproducibility Workflow

To reproduce the Phase 2 dataset from scratch:

```bash
# 1. Extract genomic chunks and sample subsets from raw chr22 VCF
python scripts/extract_genomic_chunks.py

# 2. Build and tag the workload container
docker build -t cloudpilot-workload:latest workloads/

# 3. Import image into Kind cluster (Windows/Linux)
docker save cloudpilot-workload:latest -o workloads/workload.tar
docker cp workloads/workload.tar cloudpilot-control-plane:/root/workload.tar
docker exec cloudpilot-control-plane ctr --namespace=k8s.io images import /root/workload.tar
rm workloads/workload.tar
docker exec cloudpilot-control-plane rm /root/workload.tar

# 4. Generate the 90-record genomic workload execution matrix
python scripts/build_dataset.py

# 5. Validate the dataset quality and feature variation
python scripts/validate_execution_dataset.py
```
