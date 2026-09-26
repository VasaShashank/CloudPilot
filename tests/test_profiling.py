import pytest
from pathlib import Path
from datetime import datetime
from backend.models.workflow import StageDefinition, StageStatus, StageState
from backend.profiling.feature_builder import FeatureBuilder, parse_memory_mb, CSV_HEADERS
from backend.profiling.collector import ProfilingCollector, extract_telemetry_from_logs

def test_parse_memory_mb():
    assert parse_memory_mb("1Gi") == 1024.0
    assert parse_memory_mb("2Gi") == 2048.0
    assert parse_memory_mb("512Mi") == 512.0
    assert parse_memory_mb("256m") == 256.0
    assert parse_memory_mb("1024") == 1024.0
    assert parse_memory_mb(None) == 512.0

def test_feature_builder_build_and_append(tmp_path):
    csv_file = tmp_path / "test_history.csv"
    builder = FeatureBuilder(dataset_path=csv_file)
    
    assert csv_file.exists()
    
    telemetry = {
        "region_size": 100000,
        "variant_count": 1170,
        "sample_count": 2504,
        "dataset_size_mb": 0.174,
        "runtime_seconds": 1.25,
        "actual_cpu": 0.35,
        "actual_memory_mb": 28.5,
        "timestamp": "2026-09-23 12:00:00"
    }
    
    record = builder.build_record(
        workflow_id="wf-test-1",
        stage_id="qc",
        stage_type="vcf_stats",
        requested_cpu="500m",
        requested_memory="1Gi",
        worker_count=2,
        success=True,
        telemetry=telemetry
    )
    
    assert record["workflow_id"] == "wf-test-1"
    assert record["stage_id"] == "qc"
    assert record["requested_cpu"] == "500m"
    assert record["requested_memory_mb"] == 1024.0
    assert record["worker_count"] == 2
    assert record["variant_count"] == 1170
    assert record["actual_memory_mb"] == 28.5
    
    builder.append_record(record)
    
    # Read back CSV
    lines = csv_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2  # header + 1 row
    assert "wf-test-1" in lines[1]
    assert "vcf_stats" in lines[1]

def test_extract_telemetry_from_logs():
    sample_logs = """
    [CloudPilot] qc started
    [CloudPilot] processing variants...
    [CloudPilot Profiling] {"stage_id": "qc", "variant_count": 1170, "actual_cpu": 0.42, "actual_memory_mb": 35.1}
    [CloudPilot] qc completed
    """
    telemetry = extract_telemetry_from_logs(sample_logs)
    assert telemetry is not None
    assert telemetry["stage_id"] == "qc"
    assert telemetry["variant_count"] == 1170
    assert telemetry["actual_cpu"] == 0.42

def test_profiling_collector_process_completion(tmp_path):
    csv_file = tmp_path / "collector_history.csv"
    builder = FeatureBuilder(dataset_path=csv_file)
    collector = ProfilingCollector(feature_builder=builder)
    
    stage_def = StageDefinition(
        id="filtering",
        type="filtering",
        cpu="1000m",
        memory="2Gi",
        env={"THREADS": "4"}
    )
    
    stage_status = StageStatus(
        id="filtering",
        type="filtering",
        state=StageState.COMPLETED,
        started_at=datetime(2026, 9, 23, 10, 0, 0),
        completed_at=datetime(2026, 9, 23, 10, 0, 15)
    )
    
    logs = '[CloudPilot Profiling] {"variant_count": 1500, "actual_cpu": 0.88, "actual_memory_mb": 45.0}'
    
    record = collector.process_stage_completion(
        workflow_id="wf-col-1",
        stage_def=stage_def,
        stage_status=stage_status,
        job_logs=logs
    )
    
    assert record["stage_id"] == "filtering"
    assert record["worker_count"] == 4
    assert record["requested_memory_mb"] == 2048.0
    assert record["variant_count"] == 1500
    assert record["success"] is True
    
    lines = csv_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

def test_generate_clean_genomic_dataset(tmp_path):
    raw_csv = tmp_path / "raw_history.csv"
    clean_csv = tmp_path / "clean_genomic.csv"
    builder = FeatureBuilder(dataset_path=raw_csv, genomic_dataset_path=clean_csv)
    
    # 1. Phase 1 test record
    builder.append_record(builder.build_record(
        workflow_id="wf-test-1",
        stage_id="stage-1",
        stage_type="Job",
        workload_source="phase1_test",
        telemetry={"variant_count": 0, "sample_count": 0, "region_size": 0},
        success=True
    ))
    # 2. Failed genomic record
    builder.append_record(builder.build_record(
        workflow_id="wf-gen-1",
        stage_id="qc",
        stage_type="vcf_stats",
        workload_source="genomic",
        telemetry={"variant_count": 1170, "sample_count": 100, "region_size": 100000},
        success=False
    ))
    # 3. Valid genomic record
    builder.append_record(builder.build_record(
        workflow_id="wf-gen-2",
        stage_id="qc",
        stage_type="vcf_stats",
        workload_source="genomic",
        telemetry={"variant_count": 1170, "sample_count": 500, "region_size": 100000},
        success=True
    ))
    # 4. Valid genomic record 2
    builder.append_record(builder.build_record(
        workflow_id="wf-gen-2",
        stage_id="filtering",
        stage_type="filtering",
        workload_source="genomic",
        telemetry={"variant_count": 17985, "sample_count": 2504, "region_size": 1000000},
        success=True
    ))
    
    clean_count = builder.generate_clean_genomic_dataset()
    assert clean_count == 2
    
    lines = clean_csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3  # header + 2 records
    assert "phase1_test" not in clean_csv.read_text(encoding="utf-8")
    assert "wf-gen-1" not in clean_csv.read_text(encoding="utf-8")
    assert "wf-gen-2" in clean_csv.read_text(encoding="utf-8")

