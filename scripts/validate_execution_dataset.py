#!/usr/bin/env python3
"""
scripts/validate_execution_dataset.py

Validates the quality, integrity, and variation of CloudPilot execution datasets:
- datasets/execution_history.csv (raw history)
- datasets/genomic_execution_history.csv (clean Phase 3 genomic dataset)

Performs programmatic checks for:
- Row counts and column completeness
- Stage type, region size, sample count, and variant count distributions
- Runtime, CPU, and memory ranges
- Missing values and duplicate rows
- Meaningful feature variation (> 1 unique value for key parameters)
"""

import sys
import csv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_CSV_PATH = ROOT_DIR / "datasets" / "execution_history.csv"
GENOMIC_CSV_PATH = ROOT_DIR / "datasets" / "genomic_execution_history.csv"

REQUIRED_COLUMNS = [
    "workflow_id", "stage_id", "stage_type", "workload_id", "workload_source",
    "chromosome", "region_start", "region_end", "region_size", "variant_count",
    "sample_count", "dataset_size_mb", "requested_cpu", "requested_memory_mb",
    "worker_count", "runtime_seconds", "actual_cpu", "actual_memory_mb",
    "success", "timestamp"
]

def validate_dataset(filepath: Path, is_clean_genomic: bool = False) -> bool:
    print(f"\n{'='*70}")
    print(f"Validating Dataset: {filepath.relative_to(ROOT_DIR)}")
    print(f"{'='*70}")
    
    if not filepath.exists():
        print(f"FAIL: File does not exist at {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    # 1. Column completeness
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in headers]
    if missing_cols:
        print(f"FAIL: Missing required columns: {missing_cols}")
        return False
    print(f" [PASS] All {len(REQUIRED_COLUMNS)} required columns present")

    # 2. Row count
    row_count = len(rows)
    print(f" [INFO] Total row count: {row_count}")
    if row_count == 0:
        print("FAIL: Dataset is empty.")
        return False

    # 3. Missing values check
    missing_value_count = 0
    for r_idx, r in enumerate(rows):
        for col in REQUIRED_COLUMNS:
            val = r.get(col)
            if val is None or str(val).strip() == "":
                missing_value_count += 1
    print(f" [{'PASS' if missing_value_count == 0 else 'WARN'}] Missing/empty field values: {missing_value_count}")

    # 4. Duplicate rows check
    seen = set()
    duplicates = 0
    for r in rows:
        key = tuple(r[k] for k in REQUIRED_COLUMNS if k != "timestamp")
        if key in seen:
            duplicates += 1
        seen.add(key)
    print(f" [{'PASS' if duplicates == 0 else 'WARN'}] Duplicate execution tuples: {duplicates}")

    # 5. Success/failure counts
    success_count = sum(1 for r in rows if str(r.get("success", "")).lower() in ("true", "1"))
    failure_count = row_count - success_count
    print(f" [INFO] Successful executions: {success_count} | Failed executions: {failure_count}")

    # 6. Feature variation and distributions
    stage_types = set(r["stage_type"] for r in rows)
    region_sizes = set(r["region_size"] for r in rows)
    sample_counts = set(r["sample_count"] for r in rows)
    variant_counts = set(r["variant_count"] for r in rows)
    workload_sources = set(r.get("workload_source", "") for r in rows)

    print(f" [INFO] Unique stage types ({len(stage_types)}): {sorted(list(stage_types))}")
    print(f" [INFO] Unique region sizes ({len(region_sizes)}): {sorted([int(x) for x in region_sizes if str(x).isdigit()])}")
    print(f" [INFO] Unique sample counts ({len(sample_counts)}): {sorted([int(x) for x in sample_counts if str(x).isdigit()])}")
    print(f" [INFO] Unique variant counts ({len(variant_counts)}): {sorted([int(x) for x in variant_counts if str(x).isdigit()])}")
    print(f" [INFO] Workload sources ({len(workload_sources)}): {sorted(list(workload_sources))}")

    # Numeric range metrics
    runtimes = [float(r["runtime_seconds"]) for r in rows if r.get("runtime_seconds")]
    cpus = [float(r["actual_cpu"]) for r in rows if r.get("actual_cpu")]
    mems = [float(r["actual_memory_mb"]) for r in rows if r.get("actual_memory_mb")]

    if runtimes:
        print(f" [INFO] Runtime (seconds): min={min(runtimes):.3f}, max={max(runtimes):.3f}, avg={sum(runtimes)/len(runtimes):.3f}")
    if cpus:
        print(f" [INFO] Actual CPU: min={min(cpus):.3f}, max={max(cpus):.3f}, avg={sum(cpus)/len(cpus):.3f}")
    if mems:
        print(f" [INFO] Actual Memory (MB): min={min(mems):.2f}, max={max(mems):.2f}, avg={sum(mems)/len(mems):.2f}")

    # 7. Meaningful variation checks
    passed_variation = True
    if len(region_sizes) <= 1:
        print("FAIL: region_size has <= 1 unique value.")
        passed_variation = False
    else:
        print(f" [PASS] region_size variation confirmed ({len(region_sizes)} distinct sizes)")

    if len(sample_counts) <= 1:
        print("FAIL: sample_count has <= 1 unique value.")
        passed_variation = False
    else:
        print(f" [PASS] sample_count variation confirmed ({len(sample_counts)} distinct sample tiers)")

    if len(variant_counts) <= 1:
        print("FAIL: variant_count has <= 1 unique value.")
        passed_variation = False
    else:
        print(f" [PASS] variant_count variation confirmed ({len(variant_counts)} distinct variant counts)")

    if len(set(runtimes)) <= 1:
        print("FAIL: runtime_seconds has <= 1 unique value.")
        passed_variation = False
    else:
        print(f" [PASS] runtime_seconds variation confirmed ({len(set(runtimes))} distinct values)")

    if is_clean_genomic:
        # Check that clean genomic dataset contains only successful genomic records
        if failure_count > 0:
            print(f"FAIL: Clean genomic dataset contains {failure_count} failures.")
            return False
        if any(s != "genomic" for s in workload_sources):
            print(f"FAIL: Clean genomic dataset contains non-genomic sources: {workload_sources}")
            return False
        print(" [PASS] Clean genomic dataset purity confirmed (100% successful genomic runs)")

    return passed_variation

def main():
    print("CloudPilot Phase 2 Dataset Quality Validation")
    raw_ok = validate_dataset(RAW_CSV_PATH, is_clean_genomic=False)
    genomic_ok = validate_dataset(GENOMIC_CSV_PATH, is_clean_genomic=True)

    print(f"\n{'='*70}")
    print("OVERALL VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Raw Dataset ({RAW_CSV_PATH.name}): {'PASS' if raw_ok else 'FAIL'}")
    print(f"Clean Genomic Dataset ({GENOMIC_CSV_PATH.name}): {'PASS' if genomic_ok else 'FAIL'}")

    if raw_ok and genomic_ok:
        print("\nALL PHASE 2 DATASET VALIDATION CHECKS PASSED.")
        sys.exit(0)
    else:
        print("\nSOME CHECKS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
