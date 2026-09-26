import time
import logging
from datetime import datetime, timezone

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

# Phase 4 imports — graceful degradation if models not yet trained
try:
    from backend.prediction.predictor import CloudPilotPredictor
    from backend.decision.decision_engine import DecisionEngine
    _INTELLIGENCE_AVAILABLE = True
except Exception:  # pragma: no cover
    _INTELLIGENCE_AVAILABLE = False

logger = logging.getLogger('cloudpilot')


class DAGScheduler:
    def __init__(self, job_manager: JobManager = None, profiling_collector: ProfilingCollector = None):
        self.job_manager = job_manager or JobManager()
        self.profiling_collector = profiling_collector or ProfilingCollector()

        # Phase 4: initialise predictor once per scheduler instance
        self._predictor: "CloudPilotPredictor | None" = None
        if _INTELLIGENCE_AVAILABLE:
            try:
                self._predictor = CloudPilotPredictor()
                logger.info("[CloudPilot] Phase-4 intelligence layer loaded successfully")
            except Exception as exc:
                logger.warning(f"[CloudPilot] Could not load predictor — running without intelligence: {exc}")

    # ---------------------------------------------------------------------- #
    # Public API                                                               #
    # ---------------------------------------------------------------------- #

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

        # 3. Initialise workflow status
        status = WorkflowStatus(
            workflow_id=workflow_id,
            name=workflow_def.name,
            state=WorkflowState.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        for stage_def in workflow_def.stages:
            status.stages[stage_def.id] = StageStatus(
                id=stage_def.id,
                type=stage_def.type,
                state=StageState.PENDING
            )

        # 4. Deadline tracking (Phase 4)
        workflow_start = datetime.now(timezone.utc)
        deadline_seconds = getattr(workflow_def, "deadline_seconds", None)

        # 5. Submit root stages
        completed: set[str] = set()
        failed:    set[str] = set()
        running:   set[str] = set()

        runnable = dag.get_root_stages()
        logger.info(f"[CloudPilot] Initial runnable stages: {runnable}")

        for stage_id in runnable:
            self._submit_stage(workflow_id, dag, stage_id, status, completed,
                               workflow_start, deadline_seconds)
            running.add(stage_id)

        # 6. Monitor loop
        while running:
            time.sleep(POLL_INTERVAL)

            newly_completed: list[str] = []
            newly_failed:    list[str] = []

            for stage_id in list(running):
                job_name = status.stages[stage_id].job_name

                if self.job_manager.is_job_complete(job_name):
                    logger.info(f"[CloudPilot] Stage completed: {stage_id}")
                    status.stages[stage_id].state = StageState.COMPLETED
                    status.stages[stage_id].completed_at = datetime.now(timezone.utc)
                    newly_completed.append(stage_id)

                    try:
                        logs = self.job_manager.get_job_logs(job_name)
                        stage_def = dag.get_stage_data(stage_id)
                        self.profiling_collector.process_stage_completion(
                            workflow_id, stage_def, status.stages[stage_id], logs
                        )
                    except Exception as exc:
                        logger.warning(f"Could not record profiling for {stage_id}: {exc}")

                elif self.job_manager.is_job_failed(job_name):
                    logger.error(f"[CloudPilot] Stage failed: {stage_id}")
                    status.stages[stage_id].state = StageState.FAILED
                    status.stages[stage_id].completed_at = datetime.now(timezone.utc)
                    status.stages[stage_id].error = "Kubernetes Job failed"
                    newly_failed.append(stage_id)

                    try:
                        logs = self.job_manager.get_job_logs(job_name)
                        stage_def = dag.get_stage_data(stage_id)
                        self.profiling_collector.process_stage_completion(
                            workflow_id, stage_def, status.stages[stage_id], logs
                        )
                    except Exception as exc:
                        logger.warning(f"Could not record failure profiling for {stage_id}: {exc}")

            for stage_id in newly_completed:
                running.remove(stage_id)
                completed.add(stage_id)

            for stage_id in newly_failed:
                running.remove(stage_id)
                failed.add(stage_id)
                self._mark_unreachable_downstream(dag, stage_id, completed, failed, status)

            # Find newly runnable stages after completions
            if newly_completed:
                next_runnable = dag.get_runnable_stages(completed)
                next_runnable = [
                    s for s in next_runnable
                    if s not in running and s not in completed and s not in failed
                    and status.stages[s].state == StageState.PENDING
                ]
                if next_runnable:
                    logger.info(f"[CloudPilot] Next runnable stages: {next_runnable}")
                    for stage_id in next_runnable:
                        self._submit_stage(workflow_id, dag, stage_id, status, completed,
                                           workflow_start, deadline_seconds)
                        running.add(stage_id)

        # 7. Final status
        if failed:
            status.state = WorkflowState.FAILED
            status.error = f"Stages failed: {', '.join(failed)}"
            logger.error(f"[CloudPilot] Workflow FAILED: {status.error}")
        else:
            status.state = WorkflowState.COMPLETED
            logger.info(f"[CloudPilot] Workflow COMPLETED successfully")

        status.completed_at = datetime.now(timezone.utc)
        return status

    # ---------------------------------------------------------------------- #
    # Private helpers                                                          #
    # ---------------------------------------------------------------------- #

    def _submit_stage(
        self,
        workflow_id: str,
        dag: WorkflowDAG,
        stage_id: str,
        status: WorkflowStatus,
        completed: set,
        workflow_start: datetime,
        deadline_seconds: int | None,
    ):
        """Optionally apply Phase-4 intelligence, then submit the K8s Job."""
        stage_def = dag.get_stage_data(stage_id)

        # Phase 4: intelligent resource injection
        if self._predictor is not None:
            stage_def = self._apply_intelligence(
                stage_def, dag, completed, workflow_start, deadline_seconds
            )

        job = build_job(workflow_id, stage_def)
        job_name = self.job_manager.create_job(job)

        status.stages[stage_id].state = StageState.RUNNING
        status.stages[stage_id].job_name = job_name
        status.stages[stage_id].started_at = datetime.now(timezone.utc)
        logger.info(f"[CloudPilot] Created Job: {job_name}")

    def _apply_intelligence(
        self,
        stage_def,
        dag: WorkflowDAG,
        completed: set,
        workflow_start: datetime,
        deadline_seconds: int | None,
    ):
        """
        Run Phase-3 prediction → Phase-4 decision and mutate stage_def in place
        with dynamically computed resources, returning the updated definition.
        """
        try:
            prediction = self._predictor.predict_from_stage_definition(stage_def)
        except Exception as exc:
            logger.warning(f"[CloudPilot] Prediction failed for {stage_def.id}: {exc} — skipping intelligence")
            return stage_def

        # Deadline pressure check
        deadline_pressure = self._check_deadline_pressure(
            dag, completed, workflow_start, deadline_seconds
        )

        decision = DecisionEngine.calculate_resources(prediction, deadline_pressure=deadline_pressure)

        # Inject decision into stage_def (Pydantic model copy)
        updated = stage_def.model_copy(update={
            "cpu":          decision["cpu_request"],
            "memory":       decision["memory_request"],
            "limit_memory": decision["memory_limit"],
            "env": {
                **(stage_def.env or {}),
                "THREADS": str(decision["worker_count"]),
                "CLOUDPILOT_TIER": decision["tier"],
            },
        })

        logger.info(
            f"[CloudPilot] Intelligence applied to {stage_def.id}: "
            f"tier={decision['tier']} | fallback={decision['fallback']} | "
            f"cpu={decision['cpu_request']} | mem={decision['memory_request']} | "
            f"limit={decision['memory_limit']} | workers={decision['worker_count']} | "
            f"deadline_pressure={deadline_pressure}"
        )
        return updated

    def _check_deadline_pressure(
        self,
        dag: WorkflowDAG,
        completed: set,
        workflow_start: datetime,
        deadline_seconds: int | None,
    ) -> bool:
        """
        Returns True if the predicted critical-path runtime for remaining stages
        exceeds 80 % of the remaining SLA budget.
        """
        if deadline_seconds is None or self._predictor is None:
            return False

        elapsed    = (datetime.now(timezone.utc) - workflow_start).total_seconds()
        remaining  = deadline_seconds - elapsed
        if remaining <= 0:
            return True

        # Sum predicted runtimes for all pending stages
        pending_stages = [
            s for s in dag.get_all_stages()
            if s not in completed
        ]
        total_predicted = 0.0
        for stage_id in pending_stages:
            try:
                stage_def = dag.get_stage_data(stage_id)
                pred = self._predictor.predict_from_stage_definition(stage_def)
                total_predicted += pred.get("predicted_runtime_seconds", 0.0)
            except Exception:
                pass  # prediction failure → conservative, don't flag pressure

        pressure = total_predicted > (0.80 * remaining)
        if pressure:
            logger.warning(
                f"[CloudPilot] Deadline pressure detected: "
                f"predicted_remaining={total_predicted:.1f}s, "
                f"sla_remaining={remaining:.1f}s"
            )
        return pressure

    def _mark_unreachable_downstream(
        self,
        dag: WorkflowDAG,
        failed_stage: str,
        completed: set,
        failed: set,
        status: WorkflowStatus,
    ):
        """Mark stages whose dependencies can never be fully satisfied as FAILED."""
        to_check = list(dag.get_downstream(failed_stage))
        while to_check:
            stage_id = to_check.pop(0)
            if stage_id in completed or stage_id in failed:
                continue
            deps = dag.get_dependencies(stage_id)
            if any(d in failed for d in deps):
                logger.warning(f"[CloudPilot] Stage {stage_id} cannot run (dependency failed)")
                status.stages[stage_id].state = StageState.FAILED
                status.stages[stage_id].error = f"Dependency failed: {failed_stage}"
                failed.add(stage_id)
                to_check.extend(dag.get_downstream(stage_id))
