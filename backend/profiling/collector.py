import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from backend.models.workflow import StageDefinition, StageStatus
from backend.profiling.feature_builder import FeatureBuilder

logger = logging.getLogger("cloudpilot")

PROFILING_PREFIX = "[CloudPilot Profiling]"

def extract_telemetry_from_logs(logs: str) -> Optional[Dict[str, Any]]:
    """Scan container logs for the JSON profiling line."""
    if not logs:
        return None
    for line in logs.splitlines():
        if PROFILING_PREFIX in line:
            raw_part = line.split(PROFILING_PREFIX, 1)[1].strip()
            start = raw_part.find("{")
            end = raw_part.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_part[start:end + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse profiling JSON: {e}")
    return None

class ProfilingCollector:
    def __init__(self, feature_builder: Optional[FeatureBuilder] = None):
        self.feature_builder = feature_builder or FeatureBuilder()

    def process_stage_completion(
        self,
        workflow_id: str,
        stage_def: StageDefinition,
        stage_status: StageStatus,
        job_logs: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract metrics from completed stage and save to dataset."""
        telemetry = extract_telemetry_from_logs(job_logs or "")
        
        # Calculate duration if timestamps are present
        duration = 0.0
        if stage_status.started_at and stage_status.completed_at:
            duration = round((stage_status.completed_at - stage_status.started_at).total_seconds(), 3)
            
        success = (stage_status.state.value == "COMPLETED")
        
        # Worker count can be passed in env or default to 1
        worker_count = 1
        if stage_def.env and "THREADS" in stage_def.env:
            try:
                worker_count = int(stage_def.env["THREADS"])
            except ValueError:
                worker_count = 1

        workload_id = stage_def.env.get("WORKLOAD_ID") if stage_def.env else None
        workload_source = stage_def.env.get("WORKLOAD_SOURCE") if stage_def.env else None

        record = self.feature_builder.build_record(
            workflow_id=workflow_id,
            stage_id=stage_def.id,
            stage_type=stage_def.type,
            requested_cpu=stage_def.cpu,
            requested_memory=stage_def.memory,
            worker_count=worker_count,
            success=success,
            runtime_seconds=duration,
            telemetry=telemetry,
            timestamp=datetime.utcnow().isoformat(),
            workload_id=workload_id,
            workload_source=workload_source
        )
        
        self.feature_builder.append_record(record)
        return record
