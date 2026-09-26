import pytest
from backend.decision.decision_engine import DecisionEngine

def test_decision_engine_high_confidence_normal():
    prediction = {
        "confidence": 0.85,
        "distribution_shift": "NORMAL",
        "predicted_actual_cpu": 1.0,
        "predicted_actual_memory_mb": 1024.0,
        "recommended_worker_count": 2,
        "fallback_recommended": False
    }
    
    decision = DecisionEngine.calculate_resources(prediction)
    
    assert decision["fallback"] is False
    assert decision["worker_count"] == 2
    
    # 1.0 * 1.25 = 1.25 -> 1250m
    assert decision["cpu_request"] == "1250m"
    
    # 1024 * 1.30 = 1331.2 -> ceil -> 1332Mi
    assert decision["memory_request"] == "1332Mi"
    
    # 1332 * 1.50 = 1998 -> ceil -> 1998Mi
    assert decision["memory_limit"] == "1998Mi"

def test_decision_engine_moderate_confidence():
    prediction = {
        "confidence": 0.65,
        "distribution_shift": "WARNING",
        "predicted_actual_cpu": 1.0,
        "predicted_actual_memory_mb": 1024.0,
        "recommended_worker_count": 2,
        "fallback_recommended": False
    }
    
    decision = DecisionEngine.calculate_resources(prediction)
    
    assert decision["fallback"] is False
    assert decision["worker_count"] == 2
    
    # 1.0 * 1.60 = 1.6 -> 1600m
    assert decision["cpu_request"] == "1600m"
    
    # 1024 * 1.75 = 1792 -> ceil -> 1792Mi
    assert decision["memory_request"] == "1792Mi"
    
    # 1792 * 2.0 = 3584Mi
    assert decision["memory_limit"] == "3584Mi"

def test_decision_engine_safe_fallback():
    prediction = {
        "confidence": 0.40,  # Below 0.60
        "distribution_shift": "SHIFTED",
        "predicted_actual_cpu": 0.5,
        "predicted_actual_memory_mb": 256.0,
        "recommended_worker_count": 1,
        "fallback_recommended": True
    }
    
    decision = DecisionEngine.calculate_resources(prediction)
    
    assert decision["fallback"] is True
    assert decision["worker_count"] == 4
    assert decision["cpu_request"] == "2000m"
    assert decision["memory_request"] == "2048Mi"
    assert decision["memory_limit"] == "4096Mi"

def test_decision_engine_deadline_pressure():
    prediction = {
        "confidence": 0.90,
        "distribution_shift": "NORMAL",
        "predicted_actual_cpu": 1.0,
        "predicted_actual_memory_mb": 512.0,
        "recommended_worker_count": 1,
        "fallback_recommended": False
    }
    
    # With deadline pressure
    decision = DecisionEngine.calculate_resources(prediction, deadline_pressure=True)
    
    assert decision["fallback"] is False
    # Worker count should scale up from 1 to 2
    assert decision["worker_count"] == 2
    
    # Original CPU for 1.0 is 1.25 -> 1250m
    # After pressure, it doubles to 2500m
    assert decision["cpu_request"] == "2500m"
