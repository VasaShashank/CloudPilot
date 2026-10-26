import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.models.workflow import WorkflowDefinition, StageDefinition, StageState, WorkflowState
from backend.scheduler.dag_scheduler import DAGScheduler
from backend.finops.billing import calculate_stage_cost, calculate_workflow_finops
from backend.storage.s3_storage import cloud_storage
from backend.k8s.node_types import determine_optimal_node_type, build_node_affinity, get_cluster_nodes_inventory

def test_finops_billing_calculation():
    # 1 hour run on 1 CPU, 1024 MB RAM
    cost_info = calculate_stage_cost(cpu_cores=1.0, mem_mb=1024.0, runtime_seconds=3600.0)
    assert cost_info["cpu_cost"] > 0
    assert cost_info["mem_cost"] > 0
    assert cost_info["total_cost"] == round(cost_info["cpu_cost"] + cost_info["mem_cost"], 6)

    # Multi-stage FinOps summary
    stages = [
        {"runtime_seconds": 12.0, "cloudpilot_cpu": 0.5, "cloudpilot_mem_mb": 128.0},
        {"runtime_seconds": 25.0, "cloudpilot_cpu": 0.8, "cloudpilot_mem_mb": 256.0}
    ]
    summary = calculate_workflow_finops(stages)
    assert summary.static_cost_dollars > summary.cloudpilot_cost_dollars
    assert summary.dollars_saved > 0
    assert summary.savings_pct > 0
    assert summary.projected_monthly_savings_dollars > 0

def test_s3_storage_emulator():
    # Presigned URL generation
    presigned = cloud_storage.generate_presigned_url("cloudpilot-genomics", "chunks/chr22_small_100s.vcf.gz")
    assert "https://s3.us-east-1.amazonaws.com" in presigned["presigned_url"]
    assert presigned["bucket"] == "cloudpilot-genomics"
    assert presigned["expires_at"] > 0

    # Bucket objects listing
    objects = cloud_storage.list_objects()
    assert len(objects) >= 3
    assert any("chr22" in obj["key"] for obj in objects)

def test_heterogeneous_node_types():
    # Memory-heavy stages route to r5.xlarge
    assert determine_optimal_node_type("variant_processing") == "r5.xlarge"
    assert determine_optimal_node_type("vcf_stats") == "c5.xlarge"

    # Node affinity generation
    affinity = build_node_affinity("c5.xlarge")
    assert affinity is not None
    assert affinity.node_affinity is not None

    # Inventory
    inventory = get_cluster_nodes_inventory()
    assert len(inventory) >= 3

def test_self_healing_retry_on_failure():
    wf = WorkflowDefinition(
        name="test_self_heal",
        stages=[StageDefinition(id="s1", type="variant_processing")],
        self_healing=True
    )

    with patch("backend.scheduler.dag_scheduler.JobManager") as mock_jm_cls, \
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
         patch("backend.scheduler.dag_scheduler.time.sleep"):
        mock_jm = MagicMock()
        mock_jm_cls.return_value = mock_jm

        created_jobs = []
        def mock_create(j):
            name = j.metadata.name
            created_jobs.append(name)
            return name
        mock_jm.create_job.side_effect = mock_create

        # First call fails, second call succeeds (self-healed!)
        call_count = {"failed": 0}
        def mock_is_failed(jname):
            if call_count["failed"] == 0:
                call_count["failed"] += 1
                return True
            return False
        mock_jm.is_job_failed.side_effect = mock_is_failed

        def mock_is_complete(jname):
            return call_count["failed"] > 0
        mock_jm.is_job_complete.side_effect = mock_is_complete

        scheduler = DAGScheduler(job_manager=mock_jm)
        status = scheduler.execute_workflow(wf, "wf-heal-1")

        # Must have completed after self-healing retry
        assert status.state == WorkflowState.COMPLETED
        assert status.stages["s1"].state == StageState.COMPLETED
        assert status.stages["s1"].retry_count == 1
        assert len(status.self_healing_events) == 1
        assert status.self_healing_events[0]["action"] == "Tier3_Fallback_Escalation"
        assert len(created_jobs) == 2

def test_carbon_footprint_calculation():
    from backend.finops.carbon import calculate_stage_carbon, calculate_workflow_carbon
    
    # 1 stage carbon computation
    stage_carbon = calculate_stage_carbon(cpu_cores=1.0, mem_mb=1024.0, runtime_seconds=3600.0, region="us-east-1")
    assert stage_carbon["energy_kwh"] > 0
    assert stage_carbon["emissions_gco2e"] > 0
    assert stage_carbon["power_watts"] > 0

    # Multi-stage workflow carbon computation
    stages = [
        {"runtime_seconds": 15.0, "cloudpilot_cpu": 0.5, "cloudpilot_mem_mb": 128.0},
        {"runtime_seconds": 30.0, "cloudpilot_cpu": 0.8, "cloudpilot_mem_mb": 256.0}
    ]
    res = calculate_workflow_carbon(stages, region="us-east-1")
    assert res.static_emissions_gco2e > res.cloudpilot_emissions_gco2e
    assert res.emissions_saved_gco2e > 0
    assert res.emissions_reduction_pct > 0
    assert res.trees_equivalent_annual >= 0
    assert res.cloud_region == "us-east-1"

def test_chaos_engineering_engine():
    from backend.chaos.chaos_engine import chaos_engine
    
    # Fault injection: Spot Preemption
    incident = chaos_engine.inject_fault("spot_preemption", stage_id="filtering", workflow_id="wf-test-chaos")
    assert incident["status"] == "RESOLVED"
    assert incident["fault_type"] == "spot_preemption"
    assert "migrated" in incident["recovery_action"].lower()

    # Fault injection: OOMKill
    oom_inc = chaos_engine.inject_fault("oom_spike", stage_id="variant_processing", workflow_id="wf-test-chaos")
    assert oom_inc["status"] == "RESOLVED"
    assert "auto-escalated" in oom_inc["recovery_action"].lower()

    # History audit
    history = chaos_engine.get_history()
    assert len(history) >= 2
    assert any(h["fault_type"] == "spot_preemption" for h in history)
