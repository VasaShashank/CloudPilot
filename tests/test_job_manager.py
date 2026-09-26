import pytest
from unittest.mock import MagicMock, patch
from kubernetes.client.rest import ApiException
from backend.k8s.job_manager import JobManager
from backend.k8s.job_builder import build_job
from backend.models.workflow import StageDefinition

@pytest.fixture
def mock_k8s():
    with patch("backend.k8s.job_manager.get_batch_client") as mock_batch, \
         patch("backend.k8s.job_manager.get_core_client") as mock_core, \
         patch("backend.k8s.job_manager.ensure_namespace") as mock_ns:
        batch_inst = MagicMock()
        core_inst = MagicMock()
        mock_batch.return_value = batch_inst
        mock_core.return_value = core_inst
        yield batch_inst, core_inst

def test_job_manager_create_job(mock_k8s):
    batch_inst, _ = mock_k8s
    mock_resp = MagicMock()
    mock_resp.metadata.name = "test-job-name"
    batch_inst.create_namespaced_job.return_value = mock_resp
    
    manager = JobManager()
    stage = StageDefinition(id="qc", type="job")
    job = build_job("wf-1", stage)
    job_name = manager.create_job(job)
    
    assert job_name == "test-job-name"
    batch_inst.create_namespaced_job.assert_called_once()

def test_job_manager_status_checks(mock_k8s):
    batch_inst, _ = mock_k8s
    manager = JobManager()
    
    # Active
    mock_job = MagicMock()
    mock_job.status.active = 1
    mock_job.status.succeeded = 0
    mock_job.status.failed = 0
    batch_inst.read_namespaced_job.return_value = mock_job
    
    assert manager.is_job_complete("test-job") is False
    assert manager.is_job_failed("test-job") is False
    
    # Succeeded
    mock_job.status.active = 0
    mock_job.status.succeeded = 1
    mock_job.status.failed = 0
    assert manager.is_job_complete("test-job") is True
    assert manager.is_job_failed("test-job") is False
    
    # Failed
    mock_job.status.active = 0
    mock_job.status.succeeded = 0
    mock_job.status.failed = 1
    assert manager.is_job_complete("test-job") is False
    assert manager.is_job_failed("test-job") is True

def test_job_manager_get_job_logs(mock_k8s):
    _, core_inst = mock_k8s
    manager = JobManager()
    
    # Pod found
    mock_pod = MagicMock()
    mock_pod.metadata.name = "test-pod-abc"
    core_inst.list_namespaced_pod.return_value.items = [mock_pod]
    core_inst.read_namespaced_pod_log.return_value = "stage finished ok"
    
    logs = manager.get_job_logs("test-job")
    assert logs == "stage finished ok"
    
    # No pod found
    core_inst.list_namespaced_pod.return_value.items = []
    logs = manager.get_job_logs("test-job-no-pod")
    assert "No pods found" in logs

def test_job_manager_delete_job(mock_k8s):
    batch_inst, _ = mock_k8s
    manager = JobManager()
    manager.delete_job("test-job")
    batch_inst.delete_namespaced_job.assert_called_once_with(
        name="test-job",
        namespace="cloudpilot",
        propagation_policy="Background"
    )
