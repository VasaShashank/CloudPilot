import time
import logging
from datetime import datetime

from backend.models.workflow import (
    WorkflowDefinition, WorkflowStatus, StageStatus,
    StageState, WorkflowState
)
from backend.workflow.parser import parse_workflow_file, parse_workflow_string
from backend.workflow.validator import validate_workflow
from backend.workflow.dag import WorkflowDAG
from backend.k8s.job_builder import build_job
from backend.k8s.job_manager import JobManager
from backend.config import POLL_INTERVAL

logger = logging.getLogger('cloudpilot')


class DAGScheduler:
    def __init__(self):
        self.job_manager = JobManager()
    
    def execute_workflow(self, workflow_def: WorkflowDefinition, workflow_id: str) -> WorkflowStatus:
        """Execute a complete workflow DAG on Kubernetes."""
        # 1. Validate
        validate_workflow(workflow_def)
        
        # 2. Build DAG
        dag = WorkflowDAG(workflow_def)
        logger.info(f"[CloudPilot] Parsed {len(dag.get_all_stages())} stages")
        logger.info(f"[CloudPilot] DAG validation successful")
        logger.info(f"[CloudPilot] Topological order: {dag.topological_order()}")
        logger.info(f"[CloudPilot] Parallel groups: {dag.get_parallel_groups()}")
        
        # 3. Initialize workflow status
        status = WorkflowStatus(
            workflow_id=workflow_id,
            name=workflow_def.name,
            state=WorkflowState.RUNNING,
            started_at=datetime.utcnow()
        )
        for stage_def in workflow_def.stages:
            status.stages[stage_def.id] = StageStatus(
                id=stage_def.id,
                type=stage_def.type,
                state=StageState.PENDING
            )
        
        # 4. Find and submit root stages
        completed = set()
        failed = set()
        running = set()
        
        runnable = dag.get_root_stages()
        logger.info(f"[CloudPilot] Runnable stages: {runnable}")
        
        for stage_id in runnable:
            self._submit_stage(workflow_id, dag, stage_id, status)
            running.add(stage_id)
        
        # 5. Monitor loop
        while running:
            time.sleep(POLL_INTERVAL)
            
            newly_completed = []
            newly_failed = []
            
            for stage_id in list(running):
                job_name = status.stages[stage_id].job_name
                
                if self.job_manager.is_job_complete(job_name):
                    logger.info(f"[CloudPilot] Stage completed: {stage_id}")
                    status.stages[stage_id].state = StageState.COMPLETED
                    status.stages[stage_id].completed_at = datetime.utcnow()
                    newly_completed.append(stage_id)
                    
                elif self.job_manager.is_job_failed(job_name):
                    logger.error(f"[CloudPilot] Stage failed: {stage_id}")
                    status.stages[stage_id].state = StageState.FAILED
                    status.stages[stage_id].completed_at = datetime.utcnow()
                    status.stages[stage_id].error = "Kubernetes Job failed"
                    newly_failed.append(stage_id)
            
            for stage_id in newly_completed:
                running.remove(stage_id)
                completed.add(stage_id)
            
            for stage_id in newly_failed:
                running.remove(stage_id)
                failed.add(stage_id)
                # Mark all downstream stages that can never run as FAILED
                self._mark_unreachable_downstream(dag, stage_id, completed, failed, status)
            
            # Find newly runnable stages
            if newly_completed:
                next_runnable = dag.get_runnable_stages(completed)
                # Filter out already running, completed, or failed stages
                next_runnable = [
                    s for s in next_runnable
                    if s not in running and s not in completed and s not in failed
                    and status.stages[s].state == StageState.PENDING
                ]
                if next_runnable:
                    logger.info(f"[CloudPilot] Runnable stages: {next_runnable}")
                    for stage_id in next_runnable:
                        self._submit_stage(workflow_id, dag, stage_id, status)
                        running.add(stage_id)
        
        # 6. Final status
        if failed:
            status.state = WorkflowState.FAILED
            status.error = f"Stages failed: {', '.join(failed)}"
            logger.error(f"[CloudPilot] Workflow FAILED: {status.error}")
        else:
            status.state = WorkflowState.COMPLETED
            logger.info(f"[CloudPilot] Workflow COMPLETED successfully")
        
        status.completed_at = datetime.utcnow()
        return status
    
    def _submit_stage(self, workflow_id: str, dag: WorkflowDAG, stage_id: str, status: WorkflowStatus):
        stage_def = dag.get_stage_data(stage_id)
        job = build_job(workflow_id, stage_def)
        job_name = self.job_manager.create_job(job)
        
        status.stages[stage_id].state = StageState.RUNNING
        status.stages[stage_id].job_name = job_name
        status.stages[stage_id].started_at = datetime.utcnow()
        logger.info(f"[CloudPilot] Created Job: {job_name}")
    
    def _mark_unreachable_downstream(self, dag: WorkflowDAG, failed_stage: str, 
                                       completed: set, failed: set, status: WorkflowStatus):
        """Mark stages whose dependencies can never be fully satisfied as FAILED."""
        # BFS from failed_stage through downstream
        to_check = list(dag.get_downstream(failed_stage))
        while to_check:
            stage_id = to_check.pop(0)
            if stage_id in completed or stage_id in failed:
                continue
            # Check if this stage can ever run
            deps = dag.get_dependencies(stage_id)
            if any(d in failed for d in deps):
                logger.warning(f"[CloudPilot] Stage {stage_id} cannot run (dependency failed)")
                status.stages[stage_id].state = StageState.FAILED
                status.stages[stage_id].error = f"Dependency failed: {failed_stage}"
                failed.add(stage_id)
                to_check.extend(dag.get_downstream(stage_id))
