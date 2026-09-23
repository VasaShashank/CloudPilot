import logging
from backend.models.workflow import WorkflowDefinition

logger = logging.getLogger('cloudpilot')

class WorkflowValidationError(Exception):
    pass

def validate_workflow(workflow: WorkflowDefinition) -> None:
    if not workflow.stages:
        raise WorkflowValidationError("Workflow must have at least one stage")
        
    stage_ids = set()
    for stage in workflow.stages:
        if not stage.id:
            raise WorkflowValidationError("Stage missing 'id' or 'id' is empty")
        if not stage.type:
            raise WorkflowValidationError(f"Stage '{stage.id}' missing 'type' or 'type' is empty")
        if stage.id in stage_ids:
            raise WorkflowValidationError(f"Duplicate stage ID: '{stage.id}'")
        stage_ids.add(stage.id)
        
    for stage in workflow.stages:
        for dep in stage.depends_on:
            if dep == stage.id:
                raise WorkflowValidationError(f"Stage '{stage.id}' depends on itself")
            if dep not in stage_ids:
                raise WorkflowValidationError(f"Stage '{stage.id}' depends on non-existent stage '{dep}'")
