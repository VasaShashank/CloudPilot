import pytest
from fastapi.testclient import TestClient
from backend.main import app, workflows, workflow_definitions
from backend.models.workflow import WorkflowStatus, WorkflowDefinition, StageDefinition, StageStatus, StageState, WorkflowState

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    workflows.clear()
    workflow_definitions.clear()

def test_dashboard_html_routes():
    """Verify that / and /dashboard return HTTP 200 and HTML content."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "CloudPilot" in res_root.text
    assert "Cytoscape" in res_root.text or "cytoscape" in res_root.text

    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert "Live Orchestrator" in res_dash.text

def test_api_templates():
    """Verify built-in templates are returned with valid YAML."""
    res = client.get("/api/templates")
    assert res.status_code == 200
    data = res.json()
    assert "genomic_pipeline" in data
    assert "linear" in data
    assert "parallel" in data
    assert "workflow:" in data["genomic_pipeline"]

def test_api_workloads():
    """Verify genomic chunk and cohort presets are returned."""
    res = client.get("/api/workloads")
    assert res.status_code == 200
    workloads = res.json()
    assert isinstance(workloads, list)
    assert len(workloads) > 0
    first = workloads[0]
    assert "id" in first
    assert "region_kb" in first
    assert "variants" in first

def test_workflow_dag_endpoint_404():
    """Verify 404 for non-existent workflow ID."""
    res = client.get("/workflows/nonexistent/dag")
    assert res.status_code == 404

def test_workflow_dag_endpoint_success():
    """Verify DAG elements and stage telemetry payload formatting."""
    yaml_str = """
    workflow:
      name: test_dag_wf
    stages:
      - id: s1
        type: vcf_stats
      - id: s2
        type: filtering
        depends_on: [s1]
    """
    create_res = client.post("/workflows", data={"yaml_body": yaml_str})
    assert create_res.status_code == 200
    wf_id = create_res.json()["workflow_id"]

    # Inject simulated prediction and decision
    workflows[wf_id].stages["s1"].prediction = {
        "predicted_runtime_seconds": 3.5,
        "predicted_actual_cpu": 0.45,
        "confidence": 0.94,
        "distribution_shift": "NORMAL"
    }
    workflows[wf_id].stages["s1"].decision = {
        "cpu_request": "500m",
        "memory_request": "512Mi",
        "memory_limit": "768Mi",
        "worker_count": 2,
        "tier": "HIGH_CONFIDENCE"
    }
    workflows[wf_id].stages["s1"].state = StageState.COMPLETED

    res = client.get(f"/workflows/{wf_id}/dag")
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_id"] == wf_id
    assert "elements" in data
    elements = data["elements"]

    # Expect 2 nodes + 1 edge = 3 elements
    nodes = [e for e in elements if not e["data"].get("source")]
    edges = [e for e in elements if e["data"].get("source")]

    assert len(nodes) == 2
    assert len(edges) == 1

    s1_node = next(n for n in nodes if n["data"]["id"] == "s1")
    assert s1_node["data"]["state"] == "COMPLETED"
    assert s1_node["data"]["prediction"]["confidence"] == 0.94
    assert s1_node["data"]["decision"]["tier"] == "HIGH_CONFIDENCE"

    edge = edges[0]
    assert edge["data"]["source"] == "s1"
    assert edge["data"]["target"] == "s2"
    assert edge["data"]["state"] == "COMPLETED"

    # Summary
    assert "summary" in data
    assert data["summary"]["total_predicted_runtime"] >= 3.5

def test_api_evaluation_summary():
    """Verify evaluation summary returns accurate benchmark structure."""
    res = client.get("/api/evaluation/summary")
    assert res.status_code == 200
    data = res.json()
    assert "records_evaluated" in data
    assert "metrics" in data
    metrics = data["metrics"]
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "sla" in metrics
    assert metrics["cpu"]["waste_reduction_pct"] > 0
    assert metrics["memory"]["waste_reduction_pct"] > 0
    assert metrics["sla"]["cloudpilot_violations"] == 0
