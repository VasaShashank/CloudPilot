"""
CloudPilot Spreadsheet Workflow Parser & Template Generator
===========================================================
Allows clinicians, bioinformaticians, and evaluators to input genomic 
parameters and pipeline architectures via Excel (.xlsx, .xls) or CSV 
sample sheets, automatically converting them into CloudPilot DAG workflows.
"""

import io
import math
import logging
from typing import Tuple, Dict, Any, List, Optional
import pandas as pd
import yaml

from backend.models.workflow import WorkflowDefinition, StageDefinition
from backend.workflow.validator import validate_workflow, WorkflowValidationError
from backend.workflow.dag import WorkflowDAG, CyclicDependencyError

logger = logging.getLogger("cloudpilot.spreadsheet")

# Canonical template columns and sample clinical genomic records
TEMPLATE_COLUMNS = [
    "stage_id",
    "stage_type",
    "depends_on",
    "chromosome",
    "region_size_bp",
    "variant_count",
    "sample_count",
    "dataset_size_mb",
    "threads",
    "cpu_request",
    "memory_request"
]

SAMPLE_RECORDS = [
    {
        "stage_id": "qc",
        "stage_type": "vcf_stats",
        "depends_on": "",
        "chromosome": 22,
        "region_size_bp": 100000,
        "variant_count": 1170,
        "sample_count": 100,
        "dataset_size_mb": 0.03,
        "threads": 1,
        "cpu_request": "500m",
        "memory_request": "512Mi"
    },
    {
        "stage_id": "filtering",
        "stage_type": "filtering",
        "depends_on": "qc",
        "chromosome": 22,
        "region_size_bp": 100000,
        "variant_count": 1170,
        "sample_count": 100,
        "dataset_size_mb": 0.03,
        "threads": 1,
        "cpu_request": "500m",
        "memory_request": "512Mi"
    },
    {
        "stage_id": "variant_processing",
        "stage_type": "variant_processing",
        "depends_on": "filtering",
        "chromosome": 22,
        "region_size_bp": 1000000,
        "variant_count": 17985,
        "sample_count": 500,
        "dataset_size_mb": 0.90,
        "threads": 2,
        "cpu_request": "1000m",
        "memory_request": "1Gi"
    },
    {
        "stage_id": "feature_extraction",
        "stage_type": "feature_extraction",
        "depends_on": "filtering",
        "chromosome": 22,
        "region_size_bp": 1000000,
        "variant_count": 17985,
        "sample_count": 500,
        "dataset_size_mb": 0.90,
        "threads": 2,
        "cpu_request": "1000m",
        "memory_request": "1Gi"
    },
    {
        "stage_id": "analysis",
        "stage_type": "analysis",
        "depends_on": "variant_processing,feature_extraction",
        "chromosome": 22,
        "region_size_bp": 4000000,
        "variant_count": 109665,
        "sample_count": 2504,
        "dataset_size_mb": 19.84,
        "threads": 4,
        "cpu_request": "1000m",
        "memory_request": "1Gi"
    }
]


def generate_template(file_format: str = "xlsx") -> bytes:
    """
    Generate a pre-formatted clinical sample sheet template.
    Returns bytes in either .xlsx (Excel) or .csv format.
    """
    df = pd.DataFrame(SAMPLE_RECORDS)
    
    if file_format.lower() in ("csv", "text/csv"):
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue().encode("utf-8")
        
    # Excel format
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Genomic_Workflow", index=False)
        # Auto-adjust column widths for readability
        worksheet = writer.sheets["Genomic_Workflow"]
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    return output.getvalue()


def _normalize_col_name(col: str) -> str:
    """Normalize column header: lowercase, strip, remove spaces/hyphens."""
    return str(col).strip().lower().replace(" ", "_").replace("-", "_")


def parse_spreadsheet(file_bytes: bytes, filename: str) -> Tuple[WorkflowDefinition, str]:
    """
    Parse an uploaded Excel or CSV file into a WorkflowDefinition and equivalent YAML string.
    
    Parameters
    ----------
    file_bytes : bytes
        The raw uploaded file bytes.
    filename : str
        The uploaded filename (to determine engine: .xlsx / .csv).
        
    Returns
    -------
    Tuple[WorkflowDefinition, str]
        (Validated WorkflowDefinition object, YAML manifest string)
    """
    fn_lower = filename.lower()
    try:
        if fn_lower.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif fn_lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            # Fallback: try excel first, then csv
            try:
                df = pd.read_excel(io.BytesIO(file_bytes))
            except Exception:
                df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        raise WorkflowValidationError(f"Could not read spreadsheet file '{filename}': {exc}")

    if df.empty:
        raise WorkflowValidationError("The uploaded spreadsheet is empty. Please provide at least one stage row.")

    # Map column headers to normalized versions
    col_map = {_normalize_col_name(c): c for c in df.columns}
    
    def get_val(row, *aliases, default=None):
        for alias in aliases:
            norm = _normalize_col_name(alias)
            if norm in col_map:
                val = row[col_map[norm]]
                if pd.notna(val) and str(val).strip() != "":
                    return val
        return default

    stages: List[StageDefinition] = []
    
    for idx, row in df.iterrows():
        raw_id = get_val(row, "stage_id", "id", "stage_name", "stage", default=f"stage_{idx+1}")
        stage_id = str(raw_id).strip()
        
        raw_type = get_val(row, "stage_type", "type", "operation", default="vcf_stats")
        stage_type = str(raw_type).strip()
        
        # Parse dependencies
        deps_raw = get_val(row, "depends_on", "dependencies", "parents", default="")
        depends_on: List[str] = []
        if deps_raw and str(deps_raw).strip() != "":
            # Support comma, semicolon, or space separation
            clean_deps = str(deps_raw).replace(";", ",").replace(" ", ",")
            depends_on = [d.strip() for d in clean_deps.split(",") if d.strip()]

        # Parse genomic metadata
        chromosome = str(get_val(row, "chromosome", "chr", default="22"))
        
        try:
            region_size = int(float(get_val(row, "region_size_bp", "region_size", "region", default=1000000)))
        except (ValueError, TypeError):
            region_size = 1000000

        try:
            variant_count = int(float(get_val(row, "variant_count", "variants", default=17985)))
        except (ValueError, TypeError):
            variant_count = 17985

        try:
            sample_count = int(float(get_val(row, "sample_count", "samples", default=500)))
        except (ValueError, TypeError):
            sample_count = 500

        try:
            dataset_size_mb = float(get_val(row, "dataset_size_mb", "size_mb", "file_size_mb", default=0.90))
        except (ValueError, TypeError):
            dataset_size_mb = 0.90

        try:
            threads = int(float(get_val(row, "threads", "workers", "worker_count", default=1)))
        except (ValueError, TypeError):
            threads = 1

        # Derive chunk_size label for backward compatibility
        if region_size <= 250000 and variant_count <= 5000:
            chunk_size = "small"
        elif region_size >= 3000000 or variant_count >= 50000:
            chunk_size = "large"
        else:
            chunk_size = "medium"

        # Build stage environment
        env: Dict[str, str] = {
            "CHROMOSOME": chromosome,
            "REGION_SIZE": str(region_size),
            "VARIANT_COUNT": str(variant_count),
            "SAMPLE_COUNT": str(sample_count),
            "DATASET_SIZE_MB": f"{dataset_size_mb:.4f}",
            "CHUNK_SIZE": chunk_size,
            "THREADS": str(threads),
        }

        # Resource requests / limits if specified
        cpu_req = get_val(row, "cpu_request", "cpu", default=None)
        mem_req = get_val(row, "memory_request", "memory", default=None)
        cpu_val = str(cpu_req).strip() if cpu_req else None
        mem_val = str(mem_req).strip() if mem_req else None

        stage = StageDefinition(
            id=stage_id,
            type=stage_type,
            depends_on=depends_on,
            env=env,
            cpu=cpu_val,
            memory=mem_val
        )
        stages.append(stage)

    # Derive workflow name from filename
    clean_wf_name = (
        filename.rsplit(".", 1)[0]
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
    )
    if not clean_wf_name or clean_wf_name in ("sample", "manifest", "input"):
        clean_wf_name = "genomic-spreadsheet-workflow"

    workflow_def = WorkflowDefinition(
        name=clean_wf_name,
        stages=stages,
        self_healing=True
    )

    # Validate stages and DAG structure
    validate_workflow(workflow_def)
    WorkflowDAG(workflow_def)

    # Generate equivalent YAML manifest string
    yaml_dict = {
        "workflow": {
            "name": workflow_def.name,
            "self_healing": workflow_def.self_healing,
        },
        "stages": []
    }
    
    for s in stages:
        s_dict: Dict[str, Any] = {
            "id": s.id,
            "type": s.type,
        }
        if s.depends_on:
            s_dict["depends_on"] = s.depends_on
        if s.cpu:
            s_dict["cpu"] = s.cpu
        if s.memory:
            s_dict["memory"] = s.memory
        if s.env:
            s_dict["env"] = s.env
        yaml_dict["stages"].append(s_dict)

    yaml_str = yaml.dump(yaml_dict, sort_keys=False, default_flow_style=False)
    
    logger.info(f"[Spreadsheet Parser] Successfully parsed {len(stages)} stages from '{filename}' into workflow '{clean_wf_name}'")
    return workflow_def, yaml_str
