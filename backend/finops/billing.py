"""
CloudPilot FinOps Dollar Billing Engine
======================================
Translates Kubernetes CPU core-hours and Memory GB-hours into standard
cloud provider dollar pricing (AWS EC2 / GCP Compute Engine equivalents).

Standard AWS US-East-1 (Linux On-Demand):
- vCPU Core-Hour: $0.0404
- Memory GB-Hour: $0.0050
- Spot Discount Rate: ~68% discount compared to On-Demand
"""

from typing import Dict, Any, List
from pydantic import BaseModel

AWS_CPU_CORE_HOUR_COST = 0.0404   # $ / core-hour (c5.xlarge baseline)
AWS_MEM_GB_HOUR_COST   = 0.0050   # $ / GB-hour (r5.xlarge baseline)
AWS_SPOT_DISCOUNT_PCT  = 68.0     # Average spot savings %

class FinOpsSummary(BaseModel):
    static_cost_dollars: float
    cloudpilot_cost_dollars: float
    dollars_saved: float
    savings_pct: float
    core_hours_allocated_static: float
    core_hours_allocated_cloudpilot: float
    mem_gb_hours_allocated_static: float
    mem_gb_hours_allocated_cloudpilot: float
    projected_monthly_savings_dollars: float

def calculate_stage_cost(cpu_cores: float, mem_mb: float, runtime_seconds: float, is_spot: bool = False) -> Dict[str, float]:
    """Calculate exact dollar cost for a single stage execution."""
    runtime_hours = max(0.0001, runtime_seconds / 3600.0)
    mem_gb = mem_mb / 1024.0
    
    cpu_cost = cpu_cores * runtime_hours * AWS_CPU_CORE_HOUR_COST
    mem_cost = mem_gb * runtime_hours * AWS_MEM_GB_HOUR_COST
    base_cost = cpu_cost + mem_cost
    
    if is_spot:
        final_cost = base_cost * (1.0 - (AWS_SPOT_DISCOUNT_PCT / 100.0))
    else:
        final_cost = base_cost
        
    return {
        "cpu_cost": round(cpu_cost, 6),
        "mem_cost": round(mem_cost, 6),
        "total_cost": round(final_cost, 6),
        "core_hours": round(cpu_cores * runtime_hours, 6),
        "mem_gb_hours": round(mem_gb * runtime_hours, 6)
    }

def calculate_workflow_finops(stages: List[Dict[str, Any]], workflows_per_month: int = 5000) -> FinOpsSummary:
    """Calculate aggregate FinOps billing comparison across workflow stages."""
    static_cost = 0.0
    cp_cost = 0.0
    static_core_hours = 0.0
    cp_core_hours = 0.0
    static_gb_hours = 0.0
    cp_gb_hours = 0.0

    for s in stages:
        runtime_sec = float(s.get("runtime_seconds", 5.0))
        act_runtime_sec = max(0.5, runtime_sec)
        
        # Static baseline: 1.0 CPU core, 1024 MiB (1.0 GB) RAM
        st_cost_info = calculate_stage_cost(1.0, 1024.0, act_runtime_sec)
        static_cost += st_cost_info["total_cost"]
        static_core_hours += st_cost_info["core_hours"]
        static_gb_hours += st_cost_info["mem_gb_hours"]

        # CloudPilot allocation
        cp_cpu = float(s.get("cloudpilot_cpu", 0.6))
        cp_mem = float(s.get("cloudpilot_mem_mb", 128.0))
        is_spot = bool(s.get("is_spot", False))
        
        cp_cost_info = calculate_stage_cost(cp_cpu, cp_mem, act_runtime_sec, is_spot=is_spot)
        cp_cost += cp_cost_info["total_cost"]
        cp_core_hours += cp_cost_info["core_hours"]
        cp_gb_hours += cp_cost_info["mem_gb_hours"]

    dollars_saved = max(0.0, static_cost - cp_cost)
    savings_pct = (dollars_saved / static_cost * 100.0) if static_cost > 0 else 0.0
    monthly_savings = dollars_saved * workflows_per_month

    return FinOpsSummary(
        static_cost_dollars=round(static_cost, 4),
        cloudpilot_cost_dollars=round(cp_cost, 4),
        dollars_saved=round(dollars_saved, 4),
        savings_pct=round(savings_pct, 1),
        core_hours_allocated_static=round(static_core_hours, 4),
        core_hours_allocated_cloudpilot=round(cp_core_hours, 4),
        mem_gb_hours_allocated_static=round(static_gb_hours, 4),
        mem_gb_hours_allocated_cloudpilot=round(cp_gb_hours, 4),
        projected_monthly_savings_dollars=round(monthly_savings, 2)
    )
