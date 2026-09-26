import os
import csv
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("cloudpilot")

DEFAULT_DATASET_PATH = Path(__file__).resolve().parent.parent.parent / "datasets" / "execution_history.csv"
DEFAULT_GENOMIC_DATASET_PATH = Path(__file__).resolve().parent.parent.parent / "datasets" / "genomic_execution_history.csv"

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

def parse_memory_mb(mem_str: Optional[str]) -> float:
    if not mem_str:
        return 512.0
    mem_str = str(mem_str).strip().lower()
    if mem_str.endswith("gi"):
        return float(mem_str[:-2]) * 1024
    if mem_str.endswith("mi"):
        return float(mem_str[:-2])
    if mem_str.endswith("m"):
        return float(mem_str[:-1])
    try:
        return float(mem_str)
    except ValueError:
        return 512.0

class FeatureBuilder:
<<<<<<< HEAD
    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH, genomic_dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path
        if genomic_dataset_path is not None:
            self.genomic_dataset_path = genomic_dataset_path
        elif dataset_path == DEFAULT_DATASET_PATH:
            self.genomic_dataset_path = DEFAULT_GENOMIC_DATASET_PATH
        else:
            self.genomic_dataset_path = dataset_path.parent / "genomic_execution_history.csv"
=======
    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH, genomic_dataset_path: Path = DEFAULT_GENOMIC_DATASET_PATH):
        self.dataset_path = dataset_path
        self.genomic_dataset_path = genomic_dataset_path
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
        self._ensure_dataset_file(self.dataset_path)

    def _ensure_dataset_file(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()

    def build_record(
        self,
        workflow_id: str,
        stage_id: str,
        stage_type: str,
        requested_cpu: Optional[str] = None,
        requested_memory: Optional[str] = None,
        worker_count: int = 1,
        success: bool = True,
        runtime_seconds: float = 0.0,
        telemetry: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
        workload_id: Optional[str] = None,
        workload_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Construct a standardized feature record."""
        telemetry = telemetry or {}
        
        req_mem_mb = parse_memory_mb(requested_memory)
        req_cpu = requested_cpu or "1000m"
        
        # Determine workload source
        resolved_source = workload_source or telemetry.get("workload_source")
        if not resolved_source:
            if stage_type in ("vcf_stats", "filtering", "variant_processing", "feature_extraction", "analysis"):
                resolved_source = "genomic"
            elif stage_type == "Job" and "wf-" in workflow_id:
                resolved_source = "phase1_test"
            else:
                resolved_source = "simulated"
                
        resolved_workload_id = workload_id or telemetry.get("workload_id", f"chr22_{stage_id}")
        
        # Coordinates and region
        r_start = int(telemetry.get("region_start", 16050000))
        r_size = int(telemetry.get("region_size", 100000))
        r_end = int(telemetry.get("region_end", r_start + r_size))
        
        record = {
            "workflow_id": str(workflow_id),
            "stage_id": str(stage_id),
            "stage_type": str(stage_type),
            "workload_id": str(resolved_workload_id),
            "workload_source": str(resolved_source),
            "chromosome": str(telemetry.get("chromosome", "22")),
            "region_start": r_start,
            "region_end": r_end,
            "region_size": r_size,
            "variant_count": int(telemetry.get("variant_count", 1170)),
            "sample_count": int(telemetry.get("sample_count", 2504)),
            "dataset_size_mb": float(telemetry.get("dataset_size_mb", 0.17)),
            "requested_cpu": str(req_cpu),
            "requested_memory_mb": float(req_mem_mb),
            "worker_count": int(worker_count),
            "runtime_seconds": float(telemetry.get("runtime_seconds", runtime_seconds)),
            "actual_cpu": float(telemetry.get("actual_cpu", 0.5)),
            "actual_memory_mb": float(telemetry.get("actual_memory_mb", 50.0)),
            "success": bool(success),
            "timestamp": str(timestamp or telemetry.get("timestamp") or "")
        }
        return record

    def append_record(self, record: Dict[str, Any]):
        """Append record to historical dataset CSV and to genomic dataset if applicable."""
        self._ensure_dataset_file(self.dataset_path)
        with open(self.dataset_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow(record)
        logger.info(f"[CloudPilot Profiling] Recorded stage '{record['stage_id']}' execution to {self.dataset_path.name}")

        # If it's a valid successful genomic execution, also append to clean genomic dataset
        if record.get("workload_source") == "genomic" and record.get("success") is True:
            self._ensure_dataset_file(self.genomic_dataset_path)
            with open(self.genomic_dataset_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writerow(record)

    def generate_clean_genomic_dataset(self) -> int:
        """Extract all valid genomic records from raw history into genomic_execution_history.csv."""
        if not self.dataset_path.exists():
            return 0
            
        genomic_rows = []
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Rule: valid genomic workload, completed successfully, non-zero variants
                source = row.get("workload_source", "")
                stype = row.get("stage_type", "")
                success = str(row.get("success", "")).lower() in ("true", "1")
                is_genomic = (source == "genomic")
                
                if is_genomic and success:
                    try:
                        vcount = int(row.get("variant_count", 0))
                        scount = int(row.get("sample_count", 0))
                        rsize = int(row.get("region_size", 0))
                        if vcount > 0 and scount > 0 and rsize > 0:
                            genomic_rows.append(row)
                    except ValueError:
                        continue
                        
        self._ensure_dataset_file(self.genomic_dataset_path)
        with open(self.genomic_dataset_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(genomic_rows)
            
        logger.info(f"[CloudPilot Profiling] Generated clean genomic dataset with {len(genomic_rows)} records at {self.genomic_dataset_path.name}")
        return len(genomic_rows)
