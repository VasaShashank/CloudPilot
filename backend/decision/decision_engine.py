import math
from typing import Any, Dict

class DecisionEngine:
    """
    Translates Phase 3 predictions, confidence scores, and SLA constraints 
    into dynamic Kubernetes resource requests, limits, and thread allocations.
    """
    
    @staticmethod
    def calculate_resources(prediction: Dict[str, Any], deadline_pressure: bool = False) -> Dict[str, Any]:
        """
        Calculate dynamic resources based on prediction, confidence, and shift.
        prediction dict should come from CloudPilotPredictor.predict_stage()
        
        If deadline_pressure is True, we may scale up worker count.
        """
        conf = prediction.get("confidence", 0.0)
        shift = prediction.get("distribution_shift", "SHIFTED")
        
        pred_cpu = prediction.get("predicted_actual_cpu", 1.0)
        pred_mem = prediction.get("predicted_actual_memory_mb", 512.0)
        recommended_workers = prediction.get("recommended_worker_count", 1)
        
        fallback = prediction.get("fallback_recommended", False)
        
        decision = {
            "fallback": False,
            "cpu_request": "1000m",
            "memory_request": "512Mi",
            "memory_limit": "1024Mi",
            "worker_count": recommended_workers
        }
        
        if fallback or conf < 0.60 or shift == "SHIFTED":
            decision["fallback"] = True
            decision["cpu_request"] = "2000m"
            decision["memory_request"] = "2048Mi"
            decision["memory_limit"] = "4096Mi"
            decision["worker_count"] = 4
        elif conf >= 0.80 and shift == "NORMAL":
            req_cpu_m = math.ceil(pred_cpu * 1.25 * 1000)
            req_mem_mi = math.ceil(pred_mem * 1.30)
            lim_mem_mi = math.ceil(req_mem_mi * 1.50)
            decision["cpu_request"] = f"{req_cpu_m}m"
            decision["memory_request"] = f"{req_mem_mi}Mi"
            decision["memory_limit"] = f"{lim_mem_mi}Mi"
        else: # Moderate Confidence or Warning (0.60 <= conf < 0.80 or shift == WARNING)
            req_cpu_m = math.ceil(pred_cpu * 1.60 * 1000)
            req_mem_mi = math.ceil(pred_mem * 1.75)
            lim_mem_mi = math.ceil(req_mem_mi * 2.00)
            decision["cpu_request"] = f"{req_cpu_m}m"
            decision["memory_request"] = f"{req_mem_mi}Mi"
            decision["memory_limit"] = f"{lim_mem_mi}Mi"
            
        if deadline_pressure and not decision["fallback"]:
            # Proactively increase worker_count
            if decision["worker_count"] < 4:
                decision["worker_count"] = min(4, decision["worker_count"] * 2)
                # Scale CPU allocation proportionally
                current_cpu_m = int(decision["cpu_request"].replace("m", ""))
                decision["cpu_request"] = f"{current_cpu_m * 2}m"
                
        return decision
