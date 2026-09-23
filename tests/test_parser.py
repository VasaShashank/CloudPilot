import pytest
import os
from backend.workflow.parser import parse_workflow_string, parse_workflow_file, WorkflowParseError

def test_parse_valid_linear_workflow():
    yaml_str = """
    workflow:
      name: linear_pipeline
      stages:
        - id: qc
          type: Job
        - id: preprocessing
          type: Job
          depends_on: [qc]
        - id: alignment
          type: Job
          depends_on: [preprocessing]
        - id: analysis
          type: Job
          depends_on: [alignment]
    """
    wf = parse_workflow_string(yaml_str)
    assert wf.name == "linear_pipeline"
    assert len(wf.stages) == 4
    assert wf.stages[0].id == "qc"
    assert wf.stages[1].depends_on == ["qc"]
    assert wf.stages[3].id == "analysis"

def test_parse_valid_parallel_workflow():
    yaml_str = """
    workflow:
      name: diamond_pipeline
      stages:
        - id: qc
          type: Job
        - id: preprocessing
          type: Job
          depends_on: [qc]
        - id: alignment
          type: Job
          depends_on: [preprocessing]
        - id: feature_extraction
          type: Job
          depends_on: [preprocessing]
        - id: analysis
          type: Job
          depends_on: [alignment, feature_extraction]
    """
    wf = parse_workflow_string(yaml_str)
    assert wf.name == "diamond_pipeline"
    assert len(wf.stages) == 5
    ids = [s.id for s in wf.stages]
    assert "alignment" in ids
    assert "feature_extraction" in ids

def test_parse_optional_fields():
    yaml_str = """
    workflow:
      name: options
      stages:
        - id: task1
          type: Job
          image: ubuntu:latest
          command: ["echo", "hello"]
          env:
            VAR1: value1
          cpu: "500m"
          memory: "1Gi"
    """
    wf = parse_workflow_string(yaml_str)
    s = wf.stages[0]
    assert s.image == "ubuntu:latest"
    assert s.command == ["echo", "hello"]
    assert s.env == {"VAR1": "value1"}
    assert s.cpu == "500m"
    assert s.memory == "1Gi"

def test_parse_missing_workflow_key():
    yaml_str = "something_else: []"
    with pytest.raises(WorkflowParseError):
        parse_workflow_string(yaml_str)

def test_parse_missing_stages_key():
    yaml_str = """
    workflow:
      name: only_name
    """
    with pytest.raises(WorkflowParseError):
        parse_workflow_string(yaml_str)

def test_parse_empty_stages():
    yaml_str = """
    workflow:
      name: empty
      stages: []
    """
    with pytest.raises(WorkflowParseError):
        parse_workflow_string(yaml_str)

def test_parse_missing_stage_id():
    yaml_str = """
    workflow:
      name: err
      stages:
        - type: Job
    """
    with pytest.raises(WorkflowParseError):
        parse_workflow_string(yaml_str)

def test_parse_missing_stage_type():
    yaml_str = """
    workflow:
      name: err
      stages:
        - id: task1
    """
    with pytest.raises(WorkflowParseError):
        parse_workflow_string(yaml_str)

def test_parse_invalid_yaml():
    yaml_str = """
    workflow:
      - this is [ invalid ] { yaml::
    """
    with pytest.raises(WorkflowParseError):
        parse_workflow_string(yaml_str)

def test_parse_workflow_file(tmp_path):
    yaml_str = """
    workflow:
      name: file_wf
      stages:
        - id: qc
          type: Job
    """
    f = tmp_path / "wf.yaml"
    f.write_text(yaml_str)
    wf = parse_workflow_file(str(f))
    assert wf.name == "file_wf"
    assert len(wf.stages) == 1

def test_parse_nonexistent_file():
    with pytest.raises(WorkflowParseError):
        parse_workflow_file("does_not_exist.yaml")
