import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.profiling.feature_builder import DEFAULT_GENOMIC_DATASET_PATH, parse_memory_mb

CANONICAL_STAGE_TYPES = [
    "analysis",
    "feature_extraction",
    "filtering",
    "variant_processing",
    "vcf_stats",
]

STAGE_TYPE_ALIASES = {
    "qc": "vcf_stats",
    "quality_control": "vcf_stats",
    "vcf_stats": "vcf_stats",
    "preprocessing": "filtering",
    "filtering": "filtering",
    "alignment": "variant_processing",
    "variant_processing": "variant_processing",
    "aggregation": "feature_extraction",
    "feature_extraction": "feature_extraction",
    "variant_analysis": "analysis",
    "report": "analysis",
    "analysis": "analysis",
}

RAW_NUMERIC_FEATURES = [
    "region_size",
    "variant_count",
    "sample_count",
    "dataset_size_mb",
    "requested_cpu_cores",
    "requested_memory_mb",
    "worker_count",
]

ENGINEERED_NUMERIC_FEATURES = [
    "variant_sample_millions",
    "parallel_speedup_factor",
    "variants_per_speedup",
    "genotypes_per_speedup",
    "stage_complexity_score",
    "cpu_worker_cap",
]

STAGE_ONEHOT_FEATURES = [f"stage_{st}" for st in CANONICAL_STAGE_TYPES]

ALL_FEATURE_NAMES = RAW_NUMERIC_FEATURES + ENGINEERED_NUMERIC_FEATURES + STAGE_ONEHOT_FEATURES

TARGET_COLUMNS = [
    "runtime_seconds",
    "actual_cpu",
    "actual_memory_mb",
]

WORKLOAD_CATALOG: Dict[str, Dict[str, Any]] = {
    "chr22_small_100s": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 16150000,
        "region_size": 100000,
        "variant_count": 1170,
        "sample_count": 100,
        "dataset_size_mb": 0.0301,
    },
    "chr22_small_500s": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 16150000,
        "region_size": 100000,
        "variant_count": 1170,
        "sample_count": 500,
        "dataset_size_mb": 0.0576,
    },
    "chr22_small_full": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 16150000,
        "region_size": 100000,
        "variant_count": 1170,
        "sample_count": 2504,
        "dataset_size_mb": 0.1703,
    },
    "chr22_medium_100s": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 17050000,
        "region_size": 1000000,
        "variant_count": 17985,
        "sample_count": 100,
        "dataset_size_mb": 0.4227,
    },
    "chr22_medium_500s": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 17050000,
        "region_size": 1000000,
        "variant_count": 17985,
        "sample_count": 500,
        "dataset_size_mb": 0.8977,
    },
    "chr22_medium_full": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 17050000,
        "region_size": 1000000,
        "variant_count": 17985,
        "sample_count": 2504,
        "dataset_size_mb": 2.9661,
    },
    "chr22_large_100s": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 20050000,
        "region_size": 4000000,
        "variant_count": 109665,
        "sample_count": 100,
        "dataset_size_mb": 2.6762,
    },
    "chr22_large_500s": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 20050000,
        "region_size": 4000000,
        "variant_count": 109665,
        "sample_count": 500,
        "dataset_size_mb": 5.8054,
    },
    "chr22_large_full": {
        "chromosome": "22",
        "region_start": 16050000,
        "region_end": 20050000,
        "region_size": 4000000,
        "variant_count": 109665,
        "sample_count": 2504,
        "dataset_size_mb": 19.8364,
    },
}


class FeatureMatrix:
    """
    Lightweight DataFrame-compatible tabular feature matrix backed by a 2D NumPy array
    and column name index. Works seamlessly without requiring external C-extensions.
    """

    def __init__(self, data: np.ndarray, columns: List[str]):
        arr = np.asarray(data, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        self.values = arr
        self.columns = list(columns)
        self._col_idx = {c: i for i, c in enumerate(self.columns)}

    @property
    def shape(self) -> Tuple[int, int]:
        return self.values.shape

    def __len__(self) -> int:
        return self.values.shape[0]

    def to_numpy(self, dtype=float) -> np.ndarray:
        return np.asarray(self.values, dtype=dtype)

    def __getitem__(self, key: Union[str, List[str]]) -> Union[np.ndarray, "FeatureMatrix"]:
        if isinstance(key, str):
            return self.values[:, self._col_idx[key]]
        indices = [self._col_idx[k] for k in key]
        return FeatureMatrix(self.values[:, indices], list(key))

    def slice_rows(self, indices: Union[np.ndarray, List[int]]) -> "FeatureMatrix":
        return FeatureMatrix(self.values[indices], self.columns)

    def has_nan(self) -> bool:
        return bool(np.isnan(self.values).any())


def parse_cpu_cores(cpu_val: Optional[Union[str, float, int]]) -> float:
    """Parse Kubernetes CPU string (e.g. '500m', '2000m', '1.5') into float cores."""
    if cpu_val is None:
        return 1.0
    if isinstance(cpu_val, (int, float)):
        return float(cpu_val)
    s = str(cpu_val).strip().lower()
    if not s:
        return 1.0
    if s.endswith("m"):
        try:
            return float(s[:-1]) / 1000.0
        except ValueError:
            return 1.0
    try:
        return float(s)
    except ValueError:
        return 1.0


def normalize_stage_type(stage_type: str) -> str:
    """Normalize stage_type string to canonical genomic stage type if known."""
    cleaned = str(stage_type or "").strip().lower()
    return STAGE_TYPE_ALIASES.get(cleaned, cleaned)


def resolve_workload_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in missing genomic characteristics from WORKLOAD_CATALOG if workload_id is provided."""
    wid = str(record.get("workload_id") or "").strip()
    chunk_size = str(record.get("chunk_size") or "").strip().lower()
    if not wid and chunk_size in ("small", "medium", "large"):
        wid = f"chr22_{chunk_size}_full"

    catalog_entry = WORKLOAD_CATALOG.get(wid, {})
    return {
        "workload_id": wid or "custom_workload",
        "chromosome": str(record.get("chromosome", catalog_entry.get("chromosome", "22"))),
        "region_size": int(float(record.get("region_size", catalog_entry.get("region_size", 100000)))),
        "variant_count": int(float(record.get("variant_count", catalog_entry.get("variant_count", 1170)))),
        "sample_count": int(float(record.get("sample_count", catalog_entry.get("sample_count", 2504)))),
        "dataset_size_mb": float(record.get("dataset_size_mb", catalog_entry.get("dataset_size_mb", 0.1703))),
    }


class FeaturePipeline:
    """
    Transforms raw genomic workload records or stage definitions into numeric feature vectors
    suitable for baseline, linear, and tree-based ML models.
    """

    def __init__(self, dataset_path: Path = DEFAULT_GENOMIC_DATASET_PATH):
        self.dataset_path = dataset_path
        self.feature_names: List[str] = list(ALL_FEATURE_NAMES)

    def load_dataset(self, filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Load and validate the clean genomic execution dataset rows."""
        path = filepath or self.dataset_path
        if not path.exists():
            raise FileNotFoundError(f"Genomic execution dataset not found at {path}")

        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                success_ok = str(row.get("success", "")).strip().lower() in ("true", "1")
                source_ok = str(row.get("workload_source", "genomic")).strip() == "genomic"
                wf_id = str(row.get("workflow_id", "")).strip()
                not_test = not wf_id.startswith(("wf-test", "wf-col"))
                if success_ok and source_ok and not_test:
                    rows.append(row)
        return rows

    def extract_single_features(self, record: Dict[str, Any]) -> Dict[str, float]:
        """Convert a single dictionary of stage + workload attributes into a full feature dict."""
        meta = resolve_workload_metadata(record)

        region_size = float(meta["region_size"])
        variant_count = float(meta["variant_count"])
        sample_count = float(meta["sample_count"])
        dataset_size_mb = float(meta["dataset_size_mb"])

        if "requested_cpu_cores" in record and record["requested_cpu_cores"] is not None:
            req_cpu_cores = float(record["requested_cpu_cores"])
        else:
            req_cpu_cores = parse_cpu_cores(record.get("requested_cpu", record.get("cpu", "1000m")))

        if "requested_memory_mb" in record and record["requested_memory_mb"] is not None:
            req_mem_mb = float(record["requested_memory_mb"])
        else:
            req_mem_mb = parse_memory_mb(record.get("requested_memory", record.get("memory", "512Mi")))

        worker_count = float(max(1, int(float(record.get("worker_count", 1)))))

        # Domain interaction features capturing bioinformatics computational scaling
        variant_sample_millions = (variant_count * sample_count) / 1e6
        parallel_speedup = 1.0 + (worker_count - 1.0) * 0.8
        variants_per_speedup = variant_count / parallel_speedup
        genotypes_per_speedup = variant_sample_millions / parallel_speedup
        cpu_worker_cap = min(req_cpu_cores, worker_count * 0.42)

        raw_stage = str(record.get("stage_type", "vcf_stats"))
        norm_stage = normalize_stage_type(raw_stage)

        stage_work = {
            "vcf_stats": variant_count * 0.00004 + sample_count * 0.00001,
            "filtering": variant_count * 0.00006 + sample_count * 0.00002,
            "variant_processing": variant_count * 0.00012 + (variant_count * sample_count) * 0.00000005,
            "feature_extraction": variant_count * 0.00009 + sample_count * 0.00003,
            "analysis": variant_count * 0.00007 + sample_count * 0.00004,
        }.get(norm_stage, variant_count * 0.00006 + sample_count * 0.00002)
        stage_complexity_score = max(0.4, stage_work / parallel_speedup)

        feat: Dict[str, float] = {
            "region_size": region_size,
            "variant_count": variant_count,
            "sample_count": sample_count,
            "dataset_size_mb": dataset_size_mb,
            "requested_cpu_cores": req_cpu_cores,
            "requested_memory_mb": req_mem_mb,
            "worker_count": worker_count,
            "variant_sample_millions": variant_sample_millions,
            "parallel_speedup_factor": parallel_speedup,
            "variants_per_speedup": variants_per_speedup,
            "genotypes_per_speedup": genotypes_per_speedup,
            "stage_complexity_score": stage_complexity_score,
            "cpu_worker_cap": cpu_worker_cap,
        }

        for st in CANONICAL_STAGE_TYPES:
            feat[f"stage_{st}"] = 1.0 if norm_stage == st else 0.0

        return feat

    def transform_records(self, records: List[Dict[str, Any]]) -> FeatureMatrix:
        """Transform a list of stage/workload dictionaries into a FeatureMatrix."""
        mat = []
        for r in records:
            feat = self.extract_single_features(r)
            mat.append([feat[col] for col in self.feature_names])
        return FeatureMatrix(np.array(mat, dtype=float), self.feature_names)

    def prepare_training_data(
        self, filepath: Optional[Path] = None
    ) -> Tuple[FeatureMatrix, Dict[str, np.ndarray], List[Dict[str, Any]]]:
        """
        Load dataset and return:
        - X: FeatureMatrix (n_samples, n_features)
        - y_dict: Dict mapping target name -> 1D numpy array
        - raw_rows: Original filtered list of row dicts
        """
        raw_rows = self.load_dataset(filepath)
        X = self.transform_records(raw_rows)
        y_dict: Dict[str, np.ndarray] = {}
        for target in TARGET_COLUMNS:
            y_dict[target] = np.array([float(r[target]) for r in raw_rows], dtype=float)
        return X, y_dict, raw_rows
