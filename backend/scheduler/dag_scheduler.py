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
from backend.profiling.collector import ProfilingCollector
from backend.prediction.predictor import CloudPilotPredictor
from backend.decision.decision_engine import DecisionEngine

logger = logging.getLogger('cloudpilot')


class DAGScheduler:
    def __init__(self, job_manager: JobManager = None, profiling_collector: ProfilingCollector = None, predictor: CloudPilotPredictor = None):
        self.job_manager = job_manager or JobManager()
        self.profiling_collector = profiling_collector or ProfilingCollector()
        self.predictor = predictor or CloudPilotPredictor()
        try:
            self.predictor.load_models()
        except Exception as e:
            logger.warning(f"[CloudPilot] Could not load predictor models: {e}")
    
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
        
        deadline_pressure = self._check_deadline_pressure(workflow_def, dag, status, completed)
        for stage_id in runnable:
            self._submit_stage(workflow_id, dag, stage_id, status, deadline_pressure=deadline_pressure)
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
                    
                    try:
                        logs = self.job_manager.get_job_logs(job_name)
                        stage_def = dag.get_stage_data(stage_id)
                        self.profiling_collector.process_stage_completion(
                            workflow_id, stage_def, status.stages[stage_id], logs
                        )
                    except Exception as e:
                        logger.warning(f"Could not record profiling for {stage_id}: {e}")
                    
                elif self.job_manager.is_job_failed(job_name):
                    logger.error(f"[CloudPilot] Stage failed: {stage_id}")
                    status.stages[stage_id].state = StageState.FAILED
                    status.stages[stage_id].completed_at = datetime.utcnow()
                    status.stages[stage_id].error = "Kubernetes Job failed"
                    newly_failed.append(stage_id)
                    
                    try:
                        logs = self.job_manager.get_job_logs(job_name)
                        stage_def = dag.get_stage_data(stage_id)
                        self.profiling_collector.process_stage_completion(
                            workflow_id, stage_def, status.stages[stage_id], logs
                        )
                    except Exception as e:
                        logger.warning(f"Could not record failure profiling for {stage_id}: {e}")
            
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
                    deadline_pressure = self._check_deadline_pressure(workflow_def, dag, status, completed)
                    for stage_id in next_runnable:
                        self._submit_stage(workflow_id, dag, stage_id, status, deadline_pressure=deadline_pressure)
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
    
    def _submit_stage(self, workflow_id: str, dag: WorkflowDAG, stage_id: str, status: WorkflowStatus, deadline_pressure: bool = False):
        stage_def = dag.get_stage_data(stage_id)
        
        # Apply intelligent decision engine
        try:
            prediction = self.predictor.predict_from_stage_definition(stage_def)
            decision = DecisionEngine.calculate_resources(prediction, deadline_pressure=deadline_pressure)
            
            stage_def.cpu = decision["cpu_request"]
            stage_def.memory = decision["memory_request"]
            stage_def.limit_memory = decision["memory_limit"]
            if stage_def.env is None:
                stage_def.env = {}
            stage_def.env["THREADS"] = str(decision["worker_count"])
            stage_def.env["MEMORY_LIMIT"] = decision["memory_limit"]
            
            logger.info(f"[CloudPilot] Decision for {stage_id}: {decision}")
        except Exception as e:
            logger.warning(f"[CloudPilot] Prediction/Decision failed for {stage_id}, using defaults. Error: {e}")
            
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
                
    def _check_deadline_pressure(self, workflow_def: WorkflowDefinition, dag: WorkflowDAG, status: WorkflowStatus, completed: set) -> bool:
        """Check if the remaining critical path risks violating the SLA deadline."""
        if not workflow_def.deadline_seconds:
            return False
            
        elapsed = (datetime.utcnow() - status.started_at).total_seconds()
        D_rem = workflow_def.deadline_seconds - elapsed
        if D_rem <= 0:
            return True # Already late, apply pressure
            
        try:
            # Re-evaluate remaining critical path based on predictions
            wf_pred = self.predictor.predict_workflow(workflow_def)
            stage_preds = wf_pred.get("stages", {})
            
            earliest_finish = {}
            for s in dag.topological_order():
                if s in completed:
                    earliest_finish[s] = 0.0
                else:
                    deps = dag.get_dependencies(s)
                    dep_finish = max((earliest_finish.get(d, 0.0) for d in deps), default=0.0)
                    earliest_finish[s] = dep_finish + stage_preds.get(s, {}).get("predicted_runtime_seconds", 0.0)
                    
            T_crit = max(earliest_finish.values(), default=0.0)
            
            if T_crit > 0.80 * D_rem:
                logger.info(f"[CloudPilot] Deadline pressure detected: T_crit={T_crit:.1f}s, D_rem={D_rem:.1f}s")
                return True
        except Exception as e:
            logger.warning(f"[CloudPilot] Could not calculate deadline pressure: {e}")
            
        return False
