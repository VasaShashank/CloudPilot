"""
Tests for Phase 4 — Decision Engine
=====================================
Validates all three resource-sizing tiers plus SLA deadline pressure scaling.
"""

import math
import pytest
from backend.decision.decision_engine import DecisionEngine


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pred(
    confidence=0.90,
    shift="NORMAL",
    cpu=1.0,
    mem_mb=1024.0,
    workers=2,
    fallback_recommended=False,
):
    return {
        "confidence": confidence,
        "distribution_shift": shift,
        "predicted_actual_cpu": cpu,
        "predicted_actual_memory_mb": mem_mb,
        "recommended_worker_count": workers,
        "fallback_recommended": fallback_recommended,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 — High confidence + NORMAL shift
# ─────────────────────────────────────────────────────────────────────────────

class TestTierHighConfidence:
    def test_tier_label(self):
        d = DecisionEngine.calculate_resources(_pred())
        assert d["tier"] == "high"

    def test_not_fallback(self):
        d = DecisionEngine.calculate_resources(_pred())
        assert d["fallback"] is False

    def test_cpu_request(self):
        # 1.0 * 1.25 = 1.25 → ceil(1250) m
        d = DecisionEngine.calculate_resources(_pred(cpu=1.0))
        assert d["cpu_request"] == "1250m"

    def test_memory_request(self):
        # 1024 * 1.30 = 1331.2 → ceil → 1332Mi
        d = DecisionEngine.calculate_resources(_pred(mem_mb=1024.0))
        assert d["memory_request"] == "1332Mi"

    def test_memory_limit(self):
        # 1332 * 1.50 = 1998.0 → ceil → 1998Mi
        d = DecisionEngine.calculate_resources(_pred(mem_mb=1024.0))
        assert d["memory_limit"] == "1998Mi"

    def test_worker_count_propagated(self):
        d = DecisionEngine.calculate_resources(_pred(workers=2))
        assert d["worker_count"] == 2

    def test_zero_cpu_handled(self):
        d = DecisionEngine.calculate_resources(_pred(cpu=0.0))
        assert d["cpu_request"] == "0m"

    def test_boundary_confidence_exactly_080(self):
        # exactly 0.80 + NORMAL → tier high
        d = DecisionEngine.calculate_resources(_pred(confidence=0.80))
        assert d["tier"] == "high"


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 — Moderate confidence or WARNING shift
# ─────────────────────────────────────────────────────────────────────────────

class TestTierModerateConfidence:
    def test_tier_label_low_confidence(self):
        d = DecisionEngine.calculate_resources(_pred(confidence=0.70))
        assert d["tier"] == "moderate"

    def test_tier_label_warning_shift(self):
        d = DecisionEngine.calculate_resources(_pred(shift="WARNING"))
        assert d["tier"] == "moderate"

    def test_not_fallback(self):
        d = DecisionEngine.calculate_resources(_pred(confidence=0.70))
        assert d["fallback"] is False

    def test_cpu_request_wider_headroom(self):
        # 1.0 * 1.60 = 1.60 → ceil(1600) m
        d = DecisionEngine.calculate_resources(_pred(confidence=0.70, cpu=1.0))
        assert d["cpu_request"] == "1600m"

    def test_memory_request_wider_headroom(self):
        # 1024 * 1.75 = 1792.0 → ceil → 1792Mi
        d = DecisionEngine.calculate_resources(_pred(confidence=0.70, mem_mb=1024.0))
        assert d["memory_request"] == "1792Mi"

    def test_memory_limit_2x(self):
        # 1792 * 2.0 = 3584Mi
        d = DecisionEngine.calculate_resources(_pred(confidence=0.70, mem_mb=1024.0))
        assert d["memory_limit"] == "3584Mi"

    def test_boundary_confidence_just_below_08(self):
        # 0.79 + NORMAL → moderate
        d = DecisionEngine.calculate_resources(_pred(confidence=0.79))
        assert d["tier"] == "moderate"


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3 — Safe fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestTierSafeFallback:
    def test_fallback_due_to_low_confidence(self):
        d = DecisionEngine.calculate_resources(_pred(confidence=0.40))
        assert d["fallback"] is True
        assert d["tier"] == "fallback"

    def test_fallback_due_to_shifted_distribution(self):
        d = DecisionEngine.calculate_resources(_pred(confidence=0.90, shift="SHIFTED"))
        assert d["fallback"] is True

    def test_fallback_due_to_flag(self):
        d = DecisionEngine.calculate_resources(_pred(fallback_recommended=True))
        assert d["fallback"] is True

    def test_fallback_constants(self):
        d = DecisionEngine.calculate_resources(_pred(confidence=0.10, shift="SHIFTED"))
        assert d["cpu_request"]    == DecisionEngine.FALLBACK_CPU_REQUEST
        assert d["memory_request"] == DecisionEngine.FALLBACK_MEM_REQUEST
        assert d["memory_limit"]   == DecisionEngine.FALLBACK_MEM_LIMIT
        assert d["worker_count"]   == DecisionEngine.FALLBACK_WORKERS

    def test_boundary_confidence_exactly_060(self):
        # confidence == 0.60 is still borderline; < 0.60 triggers fallback
        d_below = DecisionEngine.calculate_resources(_pred(confidence=0.599))
        assert d_below["fallback"] is True

        d_at = DecisionEngine.calculate_resources(_pred(confidence=0.60))
        assert d_at["fallback"] is False


# ─────────────────────────────────────────────────────────────────────────────
# SLA Deadline Pressure scaling
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadlinePressure:
    def test_worker_count_doubles(self):
        d = DecisionEngine.calculate_resources(_pred(workers=1), deadline_pressure=True)
        assert d["worker_count"] == 2

    def test_worker_count_capped_at_4(self):
        d = DecisionEngine.calculate_resources(_pred(workers=4), deadline_pressure=True)
        assert d["worker_count"] == 4

    def test_cpu_doubles_under_pressure(self):
        # High tier: 1.0 * 1.25 = 1.25 → * 2 = 2.50 → 2500m
        d = DecisionEngine.calculate_resources(_pred(cpu=1.0), deadline_pressure=True)
        assert d["cpu_request"] == "2500m"

    def test_no_pressure_baseline(self):
        # Without pressure, workers stay as-is
        d = DecisionEngine.calculate_resources(_pred(workers=1), deadline_pressure=False)
        assert d["worker_count"] == 1

    def test_pressure_on_moderate_tier(self):
        # Moderate: 1.0 * 1.60 = 1.60 → * 2 = 3.20 → 3200m
        d = DecisionEngine.calculate_resources(
            _pred(confidence=0.70, cpu=1.0, workers=2),
            deadline_pressure=True,
        )
        assert d["cpu_request"] == "3200m"
        assert d["worker_count"] == 4  # min(2*2, 4)

    def test_fallback_not_affected_by_pressure(self):
        # Fallback ignores pressure — returns fixed constants
        d = DecisionEngine.calculate_resources(
            _pred(confidence=0.10),
            deadline_pressure=True,
        )
        assert d["fallback"] is True
        assert d["cpu_request"] == DecisionEngine.FALLBACK_CPU_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# Return-value contract
# ─────────────────────────────────────────────────────────────────────────────

class TestReturnContract:
    REQUIRED_KEYS = {"fallback", "tier", "cpu_request", "memory_request", "memory_limit", "worker_count"}

    def test_all_keys_present_high(self):
        d = DecisionEngine.calculate_resources(_pred())
        assert self.REQUIRED_KEYS.issubset(d.keys())

    def test_all_keys_present_fallback(self):
        d = DecisionEngine.calculate_resources(_pred(confidence=0.10))
        assert self.REQUIRED_KEYS.issubset(d.keys())

    def test_cpu_string_format(self):
        d = DecisionEngine.calculate_resources(_pred())
        assert d["cpu_request"].endswith("m")

    def test_memory_string_format(self):
        d = DecisionEngine.calculate_resources(_pred())
        assert d["memory_request"].endswith("Mi")
        assert d["memory_limit"].endswith("Mi")
