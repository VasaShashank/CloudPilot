"""
CloudPilot Decision Engine — Phase 4
======================================
Translates Phase 3 ML predictions + confidence/shift scores into concrete
Kubernetes resource requests, limits, and thread allocations.

Decision tiers
--------------
1. High confidence + NORMAL shift (confidence >= 0.80):
   • Tight, efficient headroom  (+25% CPU, +30% mem)
   • Memory limit = 1.5 × request
   • worker_count = recommended_worker_count from predictor

2. Moderate confidence or WARNING shift (0.60 <= confidence < 0.80):
   • Wider headroom  (+60% CPU, +75% mem)
   • Memory limit = 2.0 × request
   • worker_count = recommended_worker_count from predictor

3. Safe fallback  (confidence < 0.60 or shift == SHIFTED):
   • Bypass ML predictions entirely
   • cpu:  "2000m", memory: "2048Mi", limit: "4096Mi", workers: 4

SLA / Deadline pressure
-----------------------
If deadline_pressure=True (critical-path runtime > 80 % of remaining budget):
   • worker_count doubles (max 4)
   • cpu_request doubles proportionally
"""

import math
import logging

logger = logging.getLogger("cloudpilot.decision")


class DecisionEngine:
    """
    Stateless utility class for resource sizing decisions.
    All methods are static — no persistent state is held.
    """

    # Safe fallback constants
    FALLBACK_CPU_REQUEST  = "2000m"
    FALLBACK_MEM_REQUEST  = "2048Mi"
    FALLBACK_MEM_LIMIT    = "4096Mi"
    FALLBACK_WORKERS      = 4

    @staticmethod
    def calculate_resources(
        prediction: dict,
        deadline_pressure: bool = False,
    ) -> dict:
        """
        Compute Kubernetes resource allocations from a prediction dict.

        Parameters
        ----------
        prediction : dict
            Output from ``CloudPilotPredictor.predict_from_stage_definition``.
            Required keys:
              - confidence            (float  in [0, 1])
              - distribution_shift    (str    "NORMAL" | "WARNING" | "SHIFTED")
              - predicted_actual_cpu  (float  in CPU cores)
              - predicted_actual_memory_mb (float in MiB)
              - recommended_worker_count   (int)
              - fallback_recommended  (bool)
        deadline_pressure : bool
            True when the critical path risks violating the SLA deadline.

        Returns
        -------
        dict with keys:
            cpu_request, memory_request, memory_limit  (str  K8s format)
            worker_count                               (int)
            fallback                                   (bool)
            tier                                       (str  "high"|"moderate"|"fallback")
        """
        confidence     = prediction.get("confidence", 0.0)
        shift          = prediction.get("distribution_shift", "SHIFTED")
        pred_cpu       = prediction.get("predicted_actual_cpu", 0.5)       # cores
        pred_mem_mb    = prediction.get("predicted_actual_memory_mb", 512) # MiB
        worker_count   = prediction.get("recommended_worker_count", 1)
        fallback_flag  = prediction.get("fallback_recommended", False)

        # ------------------------------------------------------------------ #
        # Tier 3 – Safe fallback                                               #
        # ------------------------------------------------------------------ #
        if fallback_flag or confidence < 0.60 or shift == "SHIFTED":
            logger.warning(
                "[DecisionEngine] FALLBACK triggered "
                f"(confidence={confidence:.2f}, shift={shift}, fallback_flag={fallback_flag})"
            )
            return {
                "fallback":       True,
                "tier":           "fallback",
                "cpu_request":    DecisionEngine.FALLBACK_CPU_REQUEST,
                "memory_request": DecisionEngine.FALLBACK_MEM_REQUEST,
                "memory_limit":   DecisionEngine.FALLBACK_MEM_LIMIT,
                "worker_count":   DecisionEngine.FALLBACK_WORKERS,
            }

        # ------------------------------------------------------------------ #
        # Tier 1 – High confidence + NORMAL shift                              #
        # ------------------------------------------------------------------ #
        if confidence >= 0.80 and shift == "NORMAL":
            cpu_cores   = pred_cpu * 1.25
            mem_request = math.ceil(pred_mem_mb * 1.30)
            mem_limit   = math.ceil(mem_request * 1.50)
            tier        = "high"

        # ------------------------------------------------------------------ #
        # Tier 2 – Moderate confidence or WARNING shift                        #
        # ------------------------------------------------------------------ #
        else:
            cpu_cores   = pred_cpu * 1.60
            mem_request = math.ceil(pred_mem_mb * 1.75)
            mem_limit   = math.ceil(mem_request * 2.00)
            tier        = "moderate"

        # ------------------------------------------------------------------ #
        # SLA deadline pressure — scale up parallelism                         #
        # ------------------------------------------------------------------ #
        if deadline_pressure:
            logger.warning("[DecisionEngine] Deadline pressure active — scaling up workers and CPU")
            worker_count = min(worker_count * 2, 4)
            cpu_cores    = cpu_cores * 2.0

        cpu_millicores = math.ceil(cpu_cores * 1000)
        cpu_str        = f"{cpu_millicores}m"

        result = {
            "fallback":       False,
            "tier":           tier,
            "cpu_request":    cpu_str,
            "memory_request": f"{mem_request}Mi",
            "memory_limit":   f"{mem_limit}Mi",
            "worker_count":   worker_count,
        }

        logger.info(
            f"[DecisionEngine] tier={tier} | "
            f"cpu={cpu_str} | mem_req={mem_request}Mi | mem_limit={mem_limit}Mi | "
            f"workers={worker_count} | deadline_pressure={deadline_pressure}"
        )
        return result
