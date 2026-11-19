"""
CloudPilot Heterogeneous Cloud Node Types & Placement
=====================================================
Defines simulated or real cloud VM node instance types:
- c5.xlarge: Compute-optimized (4 vCPU, 8 GiB RAM) -> vcf_stats, analysis
- r5.xlarge: Memory-optimized (4 vCPU, 32 GiB RAM) -> variant_processing, filtering
- t3.medium: General burstable (2 vCPU, 4 GiB RAM) -> lightweight jobs

Supports:
- Node affinity (nodeSelector / preferredDuringSchedulingIgnoredDuringExecution)
- Spot instance tolerations and lifecycle tracking
"""

from typing import Dict, Any, List, Optional
from kubernetes import client

CLOUD_INSTANCE_TYPES = {
    "c5.xlarge": {
        "family": "compute-optimized",
        "vcpu": 4,
        "memory_gib": 8,
        "hourly_cost": 0.170,
        "spot_hourly_cost": 0.0544,
        "labels": {"node.kubernetes.io/instance-type": "c5.xlarge", "workload-type": "compute"}
    },
    "r5.xlarge": {
        "family": "memory-optimized",
        "vcpu": 4,
        "memory_gib": 32,
        "hourly_cost": 0.252,
        "spot_hourly_cost": 0.0806,
        "labels": {"node.kubernetes.io/instance-type": "r5.xlarge", "workload-type": "memory"}
    },
    "t3.medium": {
        "family": "general-purpose",
        "vcpu": 2,
        "memory_gib": 4,
        "hourly_cost": 0.0416,
        "spot_hourly_cost": 0.0125,
        "labels": {"node.kubernetes.io/instance-type": "t3.medium", "workload-type": "general"}
    }
}

def determine_optimal_node_type(stage_type: str, predicted_mem_mb: float = 0.0) -> str:
    """Recommend node instance type based on stage characteristics and predicted footprint."""
    if stage_type in ("variant_processing", "alignment") or predicted_mem_mb > 1500.0:
        return "r5.xlarge"
    elif stage_type in ("vcf_stats", "analysis", "qc"):
        return "c5.xlarge"
    return "c5.xlarge"

def build_node_affinity(node_type: str) -> Optional[client.V1Affinity]:
    """Build Kubernetes node affinity matching the recommended instance type."""
    instance_info = CLUSTER_NODES_SPEC = CLOUD_INSTANCE_TYPES.get(node_type)
    if not instance_info:
        return None
        
    match_expressions = [
        client.V1NodeSelectorRequirement(
            key="node.kubernetes.io/instance-type",
            operator="In",
            values=[node_type]
        )
    ]
    
    preferred_scheduling = [
        client.V1PreferredSchedulingTerm(
            weight=100,
            preference=client.V1NodeSelectorTerm(
                match_expressions=match_expressions
            )
        )
    ]
    
    node_affinity = client.V1NodeAffinity(
        preferred_during_scheduling_ignored_during_execution=preferred_scheduling
    )
    return client.V1Affinity(node_affinity=node_affinity)

def get_cluster_nodes_inventory(active_stages: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Return live or simulated inventory of heterogeneous cloud nodes with Karpenter-style bin-packing."""
    active_stages = active_stages or []
    
    # Track assigned stages per node
    c5_stages = [s["stage_id"] for s in active_stages if s.get("node_type") == "c5.xlarge"]
    r5_stages = [s["stage_id"] for s in active_stages if s.get("node_type") == "r5.xlarge"]

    if not active_stages:
        c5_stages = ["vcf_stats", "analysis"]
        r5_stages = ["variant_processing", "filtering"]

    c5_cpu_used = round(len(c5_stages) * 0.618, 2)
    c5_mem_used = round(len(c5_stages) * 121.0, 1)
    r5_cpu_used = round(len(r5_stages) * 0.88, 2)
    r5_mem_used = round(len(r5_stages) * 180.0, 1)

    return [
        {
            "name": "kind-worker-compute-1",
            "instance_type": "c5.xlarge",
            "family": "compute-optimized",
            "vcpus": 4,
            "memory_gib": 8,
            "lifecycle": "spot",
            "status": "Ready",
            "autoscaler_state": "ACTIVE_PACKED",
            "cpu_allocated_cores": c5_cpu_used,
            "cpu_utilization_pct": round((c5_cpu_used / 4.0) * 100.0, 1),
            "memory_allocated_mb": c5_mem_used,
            "memory_utilization_pct": round((c5_mem_used / 8192.0) * 100.0, 1),
            "packed_pod_count": len(c5_stages),
            "assigned_stages": c5_stages
        },
        {
            "name": "kind-worker-memory-2",
            "instance_type": "r5.xlarge",
            "family": "memory-optimized",
            "vcpus": 4,
            "memory_gib": 32,
            "lifecycle": "on-demand",
            "status": "Ready",
            "autoscaler_state": "ACTIVE_PACKED",
            "cpu_allocated_cores": r5_cpu_used,
            "cpu_utilization_pct": round((r5_cpu_used / 4.0) * 100.0, 1),
            "memory_allocated_mb": r5_mem_used,
            "memory_utilization_pct": round((r5_mem_used / 32768.0) * 100.0, 1),
            "packed_pod_count": len(r5_stages),
            "assigned_stages": r5_stages
        },
        {
            "name": "kind-control-plane",
            "instance_type": "t3.medium",
            "family": "general-purpose",
            "vcpus": 2,
            "memory_gib": 4,
            "lifecycle": "on-demand",
            "status": "Ready",
            "autoscaler_state": "SYSTEM_RUNNING",
            "cpu_allocated_cores": 0.45,
            "cpu_utilization_pct": 22.5,
            "memory_allocated_mb": 1024.0,
            "memory_utilization_pct": 25.0,
            "packed_pod_count": 2,
            "assigned_stages": ["control-plane", "api-server"]
        }
    ]
