import yaml
import logging
from backend.models.workflow import StageDefinition, WorkflowDefinition

logger = logging.getLogger('cloudpilot')

class WorkflowParseError(Exception):
    pass

def parse_workflow_string(yaml_string: str) -> WorkflowDefinition:
    try:
        data = yaml.safe_load(yaml_string)
    except yaml.YAMLError as e:
        raise WorkflowParseError(f"Invalid YAML formatting: {e}")

    if not isinstance(data, dict):
        raise WorkflowParseError("Root element must be a dictionary")
    
    if "workflow" not in data or not isinstance(data["workflow"], dict):
        raise WorkflowParseError("Missing or invalid 'workflow' key")
    
    workflow_data = data["workflow"]
    
    if "name" not in workflow_data:
        raise WorkflowParseError("Workflow missing 'name'")
    
    # Support stages either nested inside 'workflow' or at top level
    if "stages" in workflow_data and isinstance(workflow_data["stages"], list):
        stages_data = workflow_data["stages"]
    elif "stages" in data and isinstance(data["stages"], list):
        stages_data = data["stages"]
    else:
        stages_data = None

    if not stages_data or len(stages_data) == 0:
        raise WorkflowParseError("Workflow missing 'stages' or 'stages' is empty")
        
    stages = []
    for idx, stage in enumerate(stages_data):
        if not isinstance(stage, dict):
            raise WorkflowParseError(f"Stage at index {idx} must be a dictionary")
        if "id" not in stage:
            raise WorkflowParseError(f"Stage at index {idx} missing 'id'")
        if "type" not in stage:
            raise WorkflowParseError(f"Stage at index {idx} missing 'type'")
            
        depends_on = stage.get("depends_on", [])
        if not isinstance(depends_on, list):
            raise WorkflowParseError(f"Stage '{stage['id']}' depends_on must be a list")
            
        stages.append(StageDefinition(
            id=stage["id"],
            type=stage["type"],
            depends_on=depends_on,
            image=stage.get("image"),
            command=stage.get("command"),
            env=stage.get("env"),
            cpu=stage.get("cpu"),
            memory=stage.get("memory")
        ))
        
    return WorkflowDefinition(
        name=workflow_data["name"],
        stages=stages
    )

def parse_workflow_file(file_path: str) -> WorkflowDefinition:
    try:
        with open(file_path, 'r') as f:
            return parse_workflow_string(f.read())
    except IOError as e:
        raise WorkflowParseError(f"Could not read file {file_path}: {e}")
