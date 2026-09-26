import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app, workflows, workflow_definitions
from backend.models.workflow import WorkflowStatus, StageStatus, StageState, WorkflowState

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    workflows.clear()
    workflow_definitions.clear()

def test_api_create_workflow_via_file_upload():
    yaml_str = """
    workflow:
      name: test_api_wf
      stages:
        - id: s1
          type: Job
        - id: s2
          type: Job
          depends_on: [s1]
    """
    resp = client.post(
        "/workflows", 
        files={"file": ("workflow.yaml", yaml_str, "text/yaml")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "workflow_id" in data
    assert data["status"]["name"] == "test_api_wf"
    assert data["status"]["state"] == "PENDING"
    wf_id = data["workflow_id"]
    assert wf_id in workflows

def test_api_create_workflow_via_yaml_body():
    yaml_str = """
    workflow:
      name: test_api_wf_body
      stages:
        - id: s1
          type: Job
    """
    resp = client.post(
        "/workflows", 
        data={"yaml_body": yaml_str}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "workflow_id" in data
    assert data["status"]["name"] == "test_api_wf_body"

def test_api_create_workflow_cyclic():
    yaml_str = """
    workflow:
      name: cyclic
      stages:
        - id: a
          type: Job
          depends_on: [b]
        - id: b
          type: Job
          depends_on: [a]
    """
    resp = client.post(
        "/workflows", 
        data={"yaml_body": yaml_str}
    )
    assert resp.status_code == 400
    assert "Cycle detected" in resp.json()["detail"]

def test_api_create_workflow_missing_input():
    resp = client.post("/workflows")
    assert resp.status_code == 400
    assert "Must provide 'file' or 'yaml_body'" in resp.json()["detail"]

def test_api_list_workflows():
    # Initially empty
    resp = client.get("/workflows")
    assert resp.status_code == 200
    assert resp.json() == []
    
    # Add one
    yaml_str = """
    workflow:
      name: wf1
      stages:
        - id: s1
          type: Job
    """
    client.post("/workflows", data={"yaml_body": yaml_str})
    resp = client.get("/workflows")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "wf1"

def test_api_get_workflow_by_id():
    resp = client.get("/workflows/nonexistent")
    assert resp.status_code == 404
    
    yaml_str = """
    workflow:
      name: wf_lookup
      stages:
        - id: s1
          type: Job
    """
    create_resp = client.post("/workflows", data={"yaml_body": yaml_str})
    wf_id = create_resp.json()["workflow_id"]
    
    resp = client.get(f"/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "wf_lookup"

def test_api_run_workflow():
    yaml_str = """
    workflow:
      name: wf_run
      stages:
        - id: s1
          type: Job
    """
    create_resp = client.post("/workflows", data={"yaml_body": yaml_str})
    wf_id = create_resp.json()["workflow_id"]
    
    with patch("backend.main.execute_workflow_bg"):
        run_resp = client.post(f"/workflows/{wf_id}/run")
        assert run_resp.status_code == 200
        assert run_resp.json()["workflow_id"] == wf_id
        assert run_resp.json()["message"] == "Workflow execution started"
        
        # Trying to run again while RUNNING should return 400
        workflows[wf_id].state = WorkflowState.RUNNING
        dup_resp = client.post(f"/workflows/{wf_id}/run")
        assert dup_resp.status_code == 400

def test_api_get_stage_logs():
    yaml_str = """
    workflow:
      name: wf_logs
      stages:
        - id: s1
          type: Job
    """
    create_resp = client.post("/workflows", data={"yaml_body": yaml_str})
    wf_id = create_resp.json()["workflow_id"]
    
    # Stage exists in status but no job_name yet -> 400
    workflows[wf_id].stages["s1"] = StageStatus(
        id="s1",
        type="Job",
        job_name=None
    )
    resp = client.get(f"/workflows/{wf_id}/stages/s1/logs")
    assert resp.status_code == 400
    
    # Mock job_name on stage status
    workflows[wf_id].stages["s1"].job_name = "cloudpilot-12345-s1"
    
    with patch("backend.main.JobManager") as mock_jm_cls:
        mock_jm = MagicMock()
        mock_jm.get_job_logs.return_value = "[CloudPilot] stage s1 completed"
        mock_jm_cls.return_value = mock_jm
        
        resp = client.get(f"/workflows/{wf_id}/stages/s1/logs")
        assert resp.status_code == 200
        assert resp.text == "[CloudPilot] stage s1 completed"
