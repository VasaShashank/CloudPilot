import pytest
from backend.workflow.validator import validate_workflow, WorkflowValidationError
from backend.models.workflow import WorkflowDefinition, StageDefinition

def test_validate_valid_workflow():
    wf = WorkflowDefinition(
        name="valid_wf",
        stages=[
            StageDefinition(id="qc", type="Job"),
            StageDefinition(id="analysis", type="Job", depends_on=["qc"])
        ]
    )
    # Should pass without exception
    validate_workflow(wf)

def test_validate_empty_stages():
    wf = WorkflowDefinition(name="empty", stages=[])
    with pytest.raises(WorkflowValidationError):
        validate_workflow(wf)

def test_validate_duplicate_stage_ids():
    wf = WorkflowDefinition(
        name="dups",
        stages=[
            StageDefinition(id="qc", type="Job"),
            StageDefinition(id="qc", type="Job")
        ]
    )
    with pytest.raises(WorkflowValidationError):
        validate_workflow(wf)

def test_validate_missing_dependency():
    wf = WorkflowDefinition(
        name="missing_dep",
        stages=[
            StageDefinition(id="analysis", type="Job", depends_on=["qc"])
        ]
    )
    with pytest.raises(WorkflowValidationError):
        validate_workflow(wf)

def test_validate_empty_stage_id():
    wf = WorkflowDefinition(
        name="empty_id",
        stages=[StageDefinition(id="", type="Job")]
    )
    with pytest.raises(WorkflowValidationError):
        validate_workflow(wf)

def test_validate_empty_stage_type():
    wf = WorkflowDefinition(
        name="empty_type",
        stages=[StageDefinition(id="qc", type="")]
    )
    with pytest.raises(WorkflowValidationError):
        validate_workflow(wf)

def test_validate_self_dependency():
    wf = WorkflowDefinition(
        name="self_dep",
        stages=[StageDefinition(id="qc", type="Job", depends_on=["qc"])]
    )
    with pytest.raises(WorkflowValidationError):
        validate_workflow(wf)

def test_validate_valid_no_dependencies():
    wf = WorkflowDefinition(
        name="no_deps",
        stages=[
            StageDefinition(id="task1", type="Job"),
            StageDefinition(id="task2", type="Job")
        ]
    )
    # Should pass
    validate_workflow(wf)
