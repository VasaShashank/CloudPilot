"""
CloudPilot Green Cloud Computing & Carbon Footprint Engine
==========================================================
Calculates real-time energy consumption (kWh) and greenhouse gas emissions (gCO2e)
based on the Green Software Foundation (GSF) and Cloud Carbon Footprint (CCF) standards.

Scientific Formula:
------------------
1. Power Draw (Watts):
   - Active CPU Power: ~10.5 Watts per physical/vCPU core under load
   - Memory Power: ~0.38 Watts per GB RAM
   - PUE (Power Usage Effectiveness): 1.18 (average hyperscale cloud datacenter)

2. Energy (Kilowatt-Hours):
   kWh = [ (CPU_Cores * 10.5W + Memory_GB * 0.38W) * PUE * Runtime_Hours ] / 1000

3. Operational Carbon Emissions (Grams of CO2e):
   Emissions (gCO2e) = Energy (kWh) * Regional Grid Carbon Intensity (gCO2e / kWh)

Regional Grid Carbon Intensities (Emissions Factors):
- us-east-1 (Virginia, USA)     : 379.2 gCO2e / kWh
- eu-west-1 (Ireland)           : 285.4 gCO2e / kWh
- ap-south-1 (Mumbai, India)    : 634.0 gCO2e / kWh
- default (Global Cloud Average): 394.0 gCO2e / kWh
"""

from typing import Dict, Any, List
from pydantic import BaseModel

# Cloud Hardware Power Parameters (Cloud Carbon Footprint standard)
CPU_WATTS_PER_CORE   = 10.5    # Watts per core under compute workload
MEMORY_WATTS_PER_GB  = 0.38    # Watts per GB DDR4/DDR5 cloud memory
DATACENTER_PUE       = 1.18    # Power Usage Effectiveness of modern cloud DCs

# Regional Grid Carbon Intensities (gCO2e / kWh)
GRID_INTENSITIES: Dict[str, float] = {
    "us-east-1": 379.2,
    "eu-west-1": 285.4,
    "ap-south-1": 634.0,
    "global-avg": 394.0
}

class CarbonFootprintResult(BaseModel):
    static_energy_kwh: float
    cloudpilot_energy_kwh: float
    energy_saved_kwh: float
    static_emissions_gco2e: float
    cloudpilot_emissions_gco2e: float
    emissions_saved_gco2e: float
    emissions_reduction_pct: float
    trees_equivalent_annual: float
    cloud_region: str
    grid_intensity_gco2e_per_kwh: float

def calculate_stage_carbon(
    cpu_cores: float,
    mem_mb: float,
    runtime_seconds: float,
    region: str = "us-east-1"
) -> Dict[str, float]:
    """Calculate real-time energy (kWh) and operational emissions (gCO2e) for a single stage."""
    runtime_hours = max(0.0001, runtime_seconds / 3600.0)
    mem_gb = mem_mb / 1024.0
    grid_intensity = GRID_INTENSITIES.get(region, GRID_INTENSITIES["global-avg"])

    # Total power draw in Watts
    total_watts = (cpu_cores * CPU_WATTS_PER_CORE + mem_gb * MEMORY_WATTS_PER_GB) * DATACENTER_PUE
    
    # Energy in Kilowatt-Hours
    energy_kwh = (total_watts * runtime_hours) / 1000.0
    
    # Carbon emissions in Grams of CO2 equivalent
    emissions_gco2e = energy_kwh * grid_intensity

    return {
        "energy_kwh": round(energy_kwh, 8),
        "emissions_gco2e": round(emissions_gco2e, 6),
        "power_watts": round(total_watts, 2)
    }

def calculate_workflow_carbon(
    stages: List[Dict[str, Any]],
    region: str = "us-east-1",
    workflows_scale_factor: int = 5000
) -> CarbonFootprintResult:
    """Calculate aggregate real-time carbon reduction across workflow stages."""
    grid_intensity = GRID_INTENSITIES.get(region, GRID_INTENSITIES["global-avg"])
    static_kwh = 0.0
    cp_kwh = 0.0
    static_gco2e = 0.0
    cp_gco2e = 0.0

    for s in stages:
        runtime_sec = float(s.get("runtime_seconds", 5.0))
        act_runtime_sec = max(0.5, runtime_sec)

        # Baseline: Static fixed 1000m CPU (1.0 core), 1024 MiB (1.0 GB) RAM
        st_metrics = calculate_stage_carbon(1.0, 1024.0, act_runtime_sec, region=region)
        static_kwh += st_metrics["energy_kwh"]
        static_gco2e += st_metrics["emissions_gco2e"]

        # CloudPilot actual allocation
        cp_cpu = float(s.get("cloudpilot_cpu", 0.6))
        cp_mem = float(s.get("cloudpilot_mem_mb", 128.0))
        cp_metrics = calculate_stage_carbon(cp_cpu, cp_mem, act_runtime_sec, region=region)
        cp_kwh += cp_metrics["energy_kwh"]
        cp_gco2e += cp_metrics["emissions_gco2e"]

    # Scale across benchmark volume
    total_static_kwh = static_kwh * workflows_scale_factor
    total_cp_kwh = cp_kwh * workflows_scale_factor
    total_static_gco2e = static_gco2e * workflows_scale_factor
    total_cp_gco2e = cp_gco2e * workflows_scale_factor

    emissions_saved = max(0.0, total_static_gco2e - total_cp_gco2e)
    energy_saved = max(0.0, total_static_kwh - total_cp_kwh)
    reduction_pct = (emissions_saved / total_static_gco2e * 100.0) if total_static_gco2e > 0 else 0.0

    # 1 urban tree absorbs ~21,770 grams of CO2 per year (EPA standard)
    trees_equivalent = round(emissions_saved / 21770.0, 3)

    return CarbonFootprintResult(
        static_energy_kwh=round(total_static_kwh, 4),
        cloudpilot_energy_kwh=round(total_cp_kwh, 4),
        energy_saved_kwh=round(energy_saved, 4),
        static_emissions_gco2e=round(total_static_gco2e, 2),
        cloudpilot_emissions_gco2e=round(total_cp_gco2e, 2),
        emissions_saved_gco2e=round(emissions_saved, 2),
        emissions_reduction_pct=round(reduction_pct, 1),
        trees_equivalent_annual=trees_equivalent,
        cloud_region=region,
        grid_intensity_gco2e_per_kwh=grid_intensity
    )
