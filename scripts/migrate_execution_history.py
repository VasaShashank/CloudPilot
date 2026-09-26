#!/usr/bin/env python3
"""
scripts/migrate_execution_history.py

Standardizes datasets/execution_history.csv to the 20-column schema:
workflow_id,stage_id,stage_type,workload_id,workload_source,chromosome,
region_start,region_end,region_size,variant_count,sample_count,dataset_size_mb,
requested_cpu,requested_memory_mb,worker_count,runtime_seconds,actual_cpu,
actual_memory_mb,success,timestamp

Corrects legacy 15-column rows and temporary overflow rows, tagging:
- Phase 1 tests as workload_source = 'phase1_test'
- Pre-existing synthetic runs as workload_source = 'simulated'
- Genomic runs as workload_source = 'genomic'
"""

import csv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT_DIR / "datasets" / "execution_history.csv"

CSV_HEADERS = [
    "workflow_id",
    "stage_id",
    "stage_type",
    "workload_id",
    "workload_source",
    "chromosome",
    "region_start",
    "region_end",
    "region_size",
    "variant_count",
    "sample_count",
    "dataset_size_mb",
    "requested_cpu",
    "requested_memory_mb",
    "worker_count",
    "runtime_seconds",
    "actual_cpu",
    "actual_memory_mb",
    "success",
    "timestamp"
]

def migrate():
    if not CSV_PATH.exists():
        print(f"File {CSV_PATH} not found.")
        return

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    if not raw_lines:
        return

    migrated_rows = []
    
    # Check first line
    header = raw_lines[0].split(",")
    is_20_col_header = (len(header) == 20 and header[3] == "workload_id")

    data_lines = raw_lines[1:]
    
    for idx, line in enumerate(data_lines):
        reader = csv.reader([line])
        fields = next(reader)
        
        # Case A: Exactly 20 columns
        if len(fields) == 20 and is_20_col_header:
            migrated_rows.append(dict(zip(CSV_HEADERS, fields)))
            continue

        # Case B: 20 fields written into a 15-column format (overflow)
        if len(fields) == 20 and not is_20_col_header:
            migrated_rows.append(dict(zip(CSV_HEADERS, fields)))
            continue

        # Case C: Legacy 15 columns
        if len(fields) == 15:
            # ['workflow_id', 'stage_id', 'stage_type', 'region_size', 'variant_count', 'sample_count',
            #  'dataset_size_mb', 'requested_cpu', 'requested_memory_mb', 'worker_count', 'runtime_seconds',
            #  'actual_cpu', 'actual_memory_mb', 'success', 'timestamp']
            wf_id, stage_id, stype, rsize, vcount, scount, dsize, rcpu, rmem, workers, rtime, acpu, amem, succ, ts = fields
            
            # Determine source
            if stype == "Job" or "wf-" in wf_id and ("parallel" in wf_id or "fail" in wf_id or "12345678" in wf_id):
                source = "phase1_test"
                workload_id = f"test_{stage_id}"
            else:
                source = "simulated"
                workload_id = f"sim_{stage_id}"

            # Safely parse numeric fields
            try:
                rsize_int = int(rsize)
            except ValueError:
                rsize_int = 100000

            try:
                vcount_int = int(vcount)
            except ValueError:
                vcount_int = 1170

            try:
                scount_int = int(scount)
            except ValueError:
                scount_int = 2504

            rstart = 16050000
            rend = rstart + rsize_int

            migrated_rows.append({
                "workflow_id": wf_id,
                "stage_id": stage_id,
                "stage_type": stype,
                "workload_id": workload_id,
                "workload_source": source,
                "chromosome": "22",
                "region_start": rstart,
                "region_end": rend,
                "region_size": rsize_int,
                "variant_count": vcount_int,
                "sample_count": scount_int,
                "dataset_size_mb": dsize,
                "requested_cpu": rcpu,
                "requested_memory_mb": rmem,
                "worker_count": workers,
                "runtime_seconds": rtime,
                "actual_cpu": acpu,
                "actual_memory_mb": amem,
                "success": succ,
                "timestamp": ts
            })

    # Write back migrated rows
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(migrated_rows)

    print(f"Successfully migrated {len(migrated_rows)} rows in {CSV_PATH.name}")

if __name__ == "__main__":
    migrate()
