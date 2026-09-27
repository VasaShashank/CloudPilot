import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from backend.scheduler.dag_scheduler import DAGScheduler
from backend.models.workflow import WorkflowDefinition, StageDefinition, StageState, WorkflowState
from backend.workflow.dag import WorkflowDAG

def test_scheduler_linear_execution():
    wf = WorkflowDefinition(
        name="test_linear",
        stages=[
            StageDefinition(id="s1", type="Job"),
            StageDefinition(id="s2", type="Job", depends_on=["s1"])
        ]
    )
    
    with patch("backend.scheduler.dag_scheduler.JobManager") as mock_jm_cls, \
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
         patch("backend.scheduler.dag_scheduler.time.sleep") as mock_sleep:
        mock_jm = MagicMock()
        mock_jm_cls.return_value = mock_jm
        
        # Track created jobs
        job_map = {}
        def mock_create(job):
            jname = job.metadata.name
            job_map[jname] = "running"
            return jname
        mock_jm.create_job.side_effect = mock_create
        
        # When polled, mark active jobs complete
        def mock_is_complete(jname):
            return True
        mock_jm.is_job_complete.side_effect = mock_is_complete
        mock_jm.is_job_failed.return_value = False
        
        scheduler = DAGScheduler()
        status = scheduler.execute_workflow(wf, "wf-12345678")
        
        assert status.state == WorkflowState.COMPLETED
        assert status.stages["s1"].state == StageState.COMPLETED
        assert status.stages["s2"].state == StageState.COMPLETED
        assert mock_jm.create_job.call_count == 2

def test_scheduler_parallel_branches():
    wf = WorkflowDefinition(
        name="test_parallel",
        stages=[
            StageDefinition(id="root", type="Job"),
            StageDefinition(id="branch_a", type="Job", depends_on=["root"]),
            StageDefinition(id="branch_b", type="Job", depends_on=["root"]),
            StageDefinition(id="join", type="Job", depends_on=["branch_a", "branch_b"])
        ]
    )
    
    with patch("backend.scheduler.dag_scheduler.JobManager") as mock_jm_cls, \
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
         patch("backend.scheduler.dag_scheduler.time.sleep"):
        mock_jm = MagicMock()
        mock_jm_cls.return_value = mock_jm
        
        def mock_create(job):
            return job.metadata.name
        mock_jm.create_job.side_effect = mock_create
        
        # Step-by-step completion simulation
        def mock_is_complete(jname):
            if "root" in jname:
                return True
            if "branch" in jname:
                return True
            if "join" in jname:
                return True
            return False
            
        mock_jm.is_job_complete.side_effect = mock_is_complete
        mock_jm.is_job_failed.return_value = False
        
        scheduler = DAGScheduler()
        status = scheduler.execute_workflow(wf, "wf-parallel")
        
        assert status.state == WorkflowState.COMPLETED
        assert status.stages["branch_a"].state == StageState.COMPLETED
        assert status.stages["branch_b"].state == StageState.COMPLETED
        assert status.stages["join"].state == StageState.COMPLETED

def test_scheduler_failure_cascades_to_downstream():
    wf = WorkflowDefinition(
        name="test_fail",
        stages=[
            StageDefinition(id="s1", type="Job"),
            StageDefinition(id="s2", type="Job", depends_on=["s1"]),
            StageDefinition(id="s3", type="Job", depends_on=["s2"])
        ]
    )
    
    with patch("backend.scheduler.dag_scheduler.JobManager") as mock_jm_cls, \
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
         patch("backend.scheduler.dag_scheduler.time.sleep"):
        mock_jm = MagicMock()
        mock_jm_cls.return_value = mock_jm
        
        mock_jm.create_job.side_effect = lambda j: j.metadata.name
        
        # s1 fails immediately
        mock_jm.is_job_complete.return_value = False
        mock_jm.is_job_failed.return_value = True
        
        scheduler = DAGScheduler()
        status = scheduler.execute_workflow(wf, "wf-fail")
        
        assert status.state == WorkflowState.FAILED
        assert status.stages["s1"].state == StageState.FAILED
        assert status.stages["s2"].state == StageState.FAILED
        assert status.stages["s3"].state == StageState.FAILED
        # Only s1 was ever submitted as a Job
        assert mock_jm.create_job.call_count == 1

def test_deadline_pressure_uses_remaining_critical_path():
    workflow = WorkflowDefinition(
        name="diamond",
        stages=[
            StageDefinition(id="root", type="Job"),
            StageDefinition(id="left", type="Job", depends_on=["root"]),
            StageDefinition(id="right", type="Job", depends_on=["root"]),
            StageDefinition(id="join", type="Job", depends_on=["left", "right"]),
        ],
    )
    scheduler = DAGScheduler.__new__(DAGScheduler)

    class Predictor:
        def predict_from_stage_definition(self, stage):
            return {"predicted_runtime_seconds": {"root": 10, "left": 30, "right": 30, "join": 10}[stage.id]}

    scheduler._predictor = Predictor()
    # Critical path is 50 seconds, while a sequential sum would be 80 seconds.
    assert scheduler._check_deadline_pressure(
        WorkflowDAG(workflow), set(), datetime.now(timezone.utc), deadline_seconds=70
    ) is False
