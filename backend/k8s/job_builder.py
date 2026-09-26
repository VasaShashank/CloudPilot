from kubernetes import client
from backend.config import WORKLOAD_IMAGE, JOB_PREFIX
from backend.models.workflow import StageDefinition

def build_job(workflow_id: str, stage: StageDefinition, image: str = WORKLOAD_IMAGE) -> client.V1Job:
    short_workflow_id = workflow_id[:8].lower().replace("_", "-")
    sanitized_stage_id = stage.id.lower().replace("_", "-")
    job_name = f"{JOB_PREFIX}-{short_workflow_id}-{sanitized_stage_id}"
    
    labels = {
        "app": "cloudpilot",
        "cloudpilot/workflow": short_workflow_id,
        "cloudpilot/stage": stage.id
    }
    
    stage_image = stage.image if stage.image else image
    
    env_vars = [
        client.V1EnvVar(name="STAGE_NAME", value=stage.id),
        client.V1EnvVar(name="STAGE_TYPE", value=stage.type)
    ]
    if stage.env:
        for k, v in stage.env.items():
            env_vars.append(client.V1EnvVar(name=k, value=str(v)))
            
    # Build resource requests
    requests = {}
    if stage.cpu:
        requests["cpu"] = stage.cpu
    if stage.memory:
        requests["memory"] = stage.memory

    # Build resource limits (Phase 4: hard ceiling to prevent OOMKills)
    limits = {}
    if stage.limit_memory:
        limits["memory"] = stage.limit_memory
    # CPU limit intentionally omitted — throttling is preferable to eviction

    resources = client.V1ResourceRequirements(
        requests=requests if requests else None,
        limits=limits if limits else None,
    )

    container = client.V1Container(
        name=sanitized_stage_id,
        image=stage_image,
        image_pull_policy="IfNotPresent",
        env=env_vars,
        command=stage.command,
        resources=resources if (requests or limits) else None
    )
    
    pod_spec = client.V1PodSpec(
        containers=[container],
        restart_policy="Never"
    )
    
    job_spec = client.V1JobSpec(
        template=client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=labels),
            spec=pod_spec
        ),
        backoff_limit=0,
        ttl_seconds_after_finished=3600
    )
    
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels=labels
        ),
        spec=job_spec
    )
    
    return job
