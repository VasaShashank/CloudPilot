"""
Tests for Spreadsheet Workflow Ingestion & Template Generation (Excel & CSV)
"""

import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app, workflows, workflow_definitions
from backend.workflow.spreadsheet_parser import (
    generate_template,
    parse_spreadsheet,
    TEMPLATE_COLUMNS,
    SAMPLE_RECORDS
)
from backend.workflow.validator import WorkflowValidationError
from backend.workflow.dag import CyclicDependencyError

client = TestClient(app)


def test_generate_excel_template():
    """Verify that generate_template('xlsx') produces valid, non-empty Excel bytes."""
    data = generate_template(file_format="xlsx")
    assert isinstance(data, bytes)
    assert len(data) > 1000

    # Read back with pandas
    df = pd.read_excel(io.BytesIO(data), sheet_name="Genomic_Workflow")
    assert len(df) == len(SAMPLE_RECORDS)
    for col in ["stage_id", "stage_type", "variant_count", "sample_count", "region_size_bp"]:
        assert col in df.columns


def test_generate_csv_template():
    """Verify that generate_template('csv') produces valid CSV text."""
    data = generate_template(file_format="csv")
    assert isinstance(data, bytes)
    text = data.decode("utf-8")
    assert "stage_id,stage_type" in text
    assert "vcf_stats" in text
    assert "variant_processing" in text


def test_parse_valid_excel_spreadsheet():
    """Test parsing an in-memory Excel workbook into a WorkflowDefinition."""
    excel_bytes = generate_template("xlsx")
    workflow_def, yaml_str = parse_spreadsheet(excel_bytes, "clinical_cohort.xlsx")

    assert workflow_def.name == "clinical-cohort"
    assert len(workflow_def.stages) == 5
    stage_ids = [s.id for s in workflow_def.stages]
    assert "qc" in stage_ids
    assert "analysis" in stage_ids

    # Check stage dependencies
    analysis_stage = next(s for s in workflow_def.stages if s.id == "analysis")
    assert "variant_processing" in analysis_stage.depends_on
    assert "feature_extraction" in analysis_stage.depends_on

    # Check environment metadata
    assert analysis_stage.env["VARIANT_COUNT"] == "109665"
    assert analysis_stage.env["SAMPLE_COUNT"] == "2504"
    assert analysis_stage.env["CHROMOSOME"] == "22"

    # Check YAML manifest output
    assert "workflow:" in yaml_str
    assert "clinical-cohort" in yaml_str


def test_parse_valid_csv_spreadsheet():
    """Test parsing a CSV into a WorkflowDefinition."""
    csv_bytes = generate_template("csv")
    workflow_def, yaml_str = parse_spreadsheet(csv_bytes, "batch_run.csv")

    assert workflow_def.name == "batch-run"
    assert len(workflow_def.stages) == 5
    assert "stages:" in yaml_str


def test_parse_custom_genomic_numbers():
    """Verify custom variant and sample numbers entered by a professor/clinician."""
    custom_rows = [
        {
            "stage_id": "custom_filtering",
            "stage_type": "filtering",
            "depends_on": "",
            "chromosome": 22,
            "region_size_bp": 3500000,
            "variant_count": 85000,
            "sample_count": 1500,
            "dataset_size_mb": 12.5,
            "threads": 4,
            "cpu_request": "1500m",
            "memory_request": "2Gi"
        }
    ]
    df = pd.DataFrame(custom_rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    
    workflow_def, yaml_str = parse_spreadsheet(buf.getvalue(), "prof_custom_test.xlsx")
    assert len(workflow_def.stages) == 1
    stage = workflow_def.stages[0]
    assert stage.id == "custom_filtering"
    assert stage.env["VARIANT_COUNT"] == "85000"
    assert stage.env["SAMPLE_COUNT"] == "1500"
    assert stage.env["THREADS"] == "4"
    assert stage.cpu == "1500m"


def test_parse_cyclic_spreadsheet_fails():
    """Test that a circular dependency in the spreadsheet is caught."""
    cyclic_rows = [
        {"stage_id": "step_a", "stage_type": "qc", "depends_on": "step_b"},
        {"stage_id": "step_b", "stage_type": "analysis", "depends_on": "step_a"},
    ]
    df = pd.DataFrame(cyclic_rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)

    with pytest.raises((CyclicDependencyError, WorkflowValidationError)):
        parse_spreadsheet(buf.getvalue(), "cyclic.xlsx")


def test_api_download_template_endpoints():
    """Test GET /api/workflows/template/spreadsheet for both xlsx and csv."""
    # Test Excel
    res_xlsx = client.get("/api/workflows/template/spreadsheet?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "application/vnd.openxmlformats" in res_xlsx.headers["content-type"]
    assert len(res_xlsx.content) > 1000

    # Test CSV
    res_csv = client.get("/api/workflows/template/spreadsheet?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "vcf_stats" in res_csv.text


def test_api_upload_spreadsheet_endpoint():
    """Test POST /api/workflows/upload-spreadsheet with an Excel file."""
    excel_bytes = generate_template("xlsx")
    files = {
        "file": ("lab_cohort_study.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }

    res = client.post("/api/workflows/upload-spreadsheet", files=files)
    assert res.status_code == 200
    data = res.json()

    assert "workflow_id" in data
    assert data["name"] == "lab-cohort-study"
    assert data["stage_count"] == 5
    assert "yaml_manifest" in data
    assert data["status"]["state"] == "PENDING"

    # Verify registered in memory
    wf_id = data["workflow_id"]
    assert wf_id in workflows
    assert wf_id in workflow_definitions

    # Test DAG retrieval for the uploaded spreadsheet workflow
    dag_res = client.get(f"/workflows/{wf_id}/dag")
    assert dag_res.status_code == 200
    dag_data = dag_res.json()
    assert len(dag_data["elements"]) > 0
