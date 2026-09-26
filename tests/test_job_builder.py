import pytest
from backend.k8s.job_builder import build_job
from backend.models.workflow import StageDefinition
from backend.config import WORKLOAD_IMAGE, JOB_PREFIX

def test_build_job_defaults():
    stage = StageDefinition(id="qc", type="quality_control")
    job = build_job("wf-12345678", stage)
    
    assert job.api_version == "batch/v1"
    assert job.kind == "Job"
    assert job.metadata.name == f"{JOB_PREFIX}-wf-12345-qc"
    assert job.metadata.labels["app"] == "cloudpilot"
    assert job.metadata.labels["cloudpilot/workflow"] == "wf-12345"
    assert job.metadata.labels["cloudpilot/stage"] == "qc"
    
    pod_spec = job.spec.template.spec
    assert pod_spec.restart_policy == "Never"
    assert len(pod_spec.containers) == 1
    
    container = pod_spec.containers[0]
    assert container.name == "qc"
    assert container.image == WORKLOAD_IMAGE
    assert container.image_pull_policy == "IfNotPresent"
    
    env_map = {e.name: e.value for e in container.env}
    assert env_map["STAGE_NAME"] == "qc"
    assert env_map["STAGE_TYPE"] == "quality_control"
    assert job.spec.backoff_limit == 0
    assert job.spec.ttl_seconds_after_finished == 3600

def test_build_job_with_custom_image_and_resources():
    stage = StageDefinition(
        id="align",
        type="alignment",
        image="custom/aligner:v1",
        cpu="2000m",
        memory="4Gi",
        command=["run_alignment.sh", "--fast"],
        env={"THREADS": "4", "OPT_LEVEL": "2"}
    )
    job = build_job("wf-abcdef123", stage)
    container = job.spec.template.spec.containers[0]
    
    assert container.image == "custom/aligner:v1"
    assert container.command == ["run_alignment.sh", "--fast"]
    assert container.resources.requests["cpu"] == "2000m"
    assert container.resources.requests["memory"] == "4Gi"
    
    env_map = {e.name: e.value for e in container.env}
    assert env_map["STAGE_NAME"] == "align"
    assert env_map["STAGE_TYPE"] == "alignment"
    assert env_map["THREADS"] == "4"
    assert env_map["OPT_LEVEL"] == "2"
