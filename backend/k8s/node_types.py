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
from kubernetes.utils.quantity import parse_quantity
from backend.config import NAMESPACE
from backend.k8s.client import get_core_client

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
    instance_info = CLOUD_INSTANCE_TYPES.get(node_type)
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
    """Return actual node capacity and CloudPilot pod requests from Kubernetes."""
    core = get_core_client()
    nodes = core.list_node(_request_timeout=5).items
    pods = core.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector="app=cloudpilot",
        _request_timeout=5
    ).items

    pods_by_node = {}
    for pod in pods:
        node_name = pod.spec.node_name
        if not node_name or pod.status.phase in ("Succeeded", "Failed"):
            continue
        pods_by_node.setdefault(node_name, []).append(pod)

    inventory = []
    for node in nodes:
        labels = node.metadata.labels or {}
        instance_type = labels.get("node.kubernetes.io/instance-type", "unknown")
        instance_info = CLOUD_INSTANCE_TYPES.get(instance_type, {})
        allocatable = node.status.allocatable or {}
        cpu_capacity = float(parse_quantity(allocatable.get("cpu", "0")))
        memory_capacity = float(parse_quantity(allocatable.get("memory", "0"))) / (1024 ** 3)
        node_pods = pods_by_node.get(node.metadata.name, [])
        cpu_requested = 0.0
        memory_requested_mb = 0.0
        stages = []

        for pod in node_pods:
            for container in pod.spec.containers:
                requests = (container.resources.requests or {}) if container.resources else {}
                cpu_requested += float(parse_quantity(requests.get("cpu", "0")))
                memory_requested_mb += float(parse_quantity(requests.get("memory", "0"))) / (1024 ** 2)
            stage = (pod.metadata.labels or {}).get("cloudpilot/stage")
            if stage:
                stages.append(stage)

        ready = any(
            condition.type == "Ready" and condition.status == "True"
            for condition in (node.status.conditions or [])
        )
        inventory.append({
            "name": node.metadata.name,
            "instance_type": instance_type,
            "family": instance_info.get("family", "unknown"),
            "vcpus": cpu_capacity,
            "memory_gib": round(memory_capacity, 2),
            "lifecycle": labels.get("node.kubernetes.io/lifecycle", "unknown"),
            "status": "Ready" if ready else "NotReady",
            "autoscaler_state": "NOT_CONFIGURED",
            "cpu_allocated_cores": round(cpu_requested, 3),
            "cpu_utilization_pct": None,
            "cpu_requested_pct": round(cpu_requested / cpu_capacity * 100, 1) if cpu_capacity else 0.0,
            "memory_allocated_mb": round(memory_requested_mb, 1),
            "memory_utilization_pct": None,
            "memory_requested_pct": round(memory_requested_mb / (memory_capacity * 1024) * 100, 1) if memory_capacity else 0.0,
            "resource_metric_type": "pod_requests",
            "packed_pod_count": len(node_pods),
            "assigned_stages": stages
        })
    return inventory
