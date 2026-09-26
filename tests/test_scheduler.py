import pytest
from unittest.mock import MagicMock, patch
from backend.scheduler.dag_scheduler import DAGScheduler
from backend.models.workflow import WorkflowDefinition, StageDefinition, StageState, WorkflowState

def test_scheduler_linear_execution():
    wf = WorkflowDefinition(
        name="test_linear",
        stages=[
            StageDefinition(id="s1", type="Job"),
            StageDefinition(id="s2", type="Job", depends_on=["s1"])
        ]
    )
    
    with patch("backend.scheduler.dag_scheduler.JobManager") as mock_jm_cls, \
<<<<<<< HEAD
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
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
<<<<<<< HEAD
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
         patch("backend.scheduler.dag_scheduler.time.sleep"):
        mock_jm = MagicMock()
        mock_jm_cls.return_value = mock_jm
        
        completed_jobs = set()
        def mock_create(job):
            return job.metadata.name
        mock_jm.create_job.side_effect = mock_create
        
        # Step-by-step completion simulation
        call_step = {"count": 0}
        def mock_is_complete(jname):
            # In first step root completes
            if "root" in jname:
                return True
            # In later step branches complete
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
<<<<<<< HEAD
         patch("backend.scheduler.dag_scheduler.ProfilingCollector"), \
=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
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
