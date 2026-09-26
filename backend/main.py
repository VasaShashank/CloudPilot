import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import uuid
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.workflow.parser import parse_workflow_file, parse_workflow_string, WorkflowParseError
from backend.workflow.validator import validate_workflow, WorkflowValidationError
from backend.workflow.dag import WorkflowDAG, CyclicDependencyError
from backend.scheduler.dag_scheduler import DAGScheduler
from backend.models.workflow import WorkflowStatus, WorkflowDefinition, WorkflowState
from backend.config import API_HOST, API_PORT
from backend.k8s.job_manager import JobManager
<<<<<<< HEAD
from backend.prediction.predictor import CloudPilotPredictor
=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger('cloudpilot')

<<<<<<< HEAD
app = FastAPI(title="CloudPilot API")

workflows: dict[str, WorkflowStatus] = {}
workflow_definitions: dict[str, WorkflowDefinition] = {}
_predictor: Optional[CloudPilotPredictor] = None


def get_predictor() -> CloudPilotPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CloudPilotPredictor().load_models()
    return _predictor

=======
app = FastAPI(title="CloudPilot Phase 1 API")

workflows: dict[str, WorkflowStatus] = {}
workflow_definitions: dict[str, WorkflowDefinition] = {}
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

class RunResponse(BaseModel):
    message: str
    workflow_id: str

@app.post("/workflows")
async def create_workflow(file: Optional[UploadFile] = File(None), yaml_body: str = Body(None)):
    try:
        if file:
            content = await file.read()
            yaml_str = content.decode('utf-8')
        elif yaml_body:
            yaml_str = yaml_body
        else:
            raise HTTPException(status_code=400, detail="Must provide 'file' or 'yaml_body'")
            
        workflow_def = parse_workflow_string(yaml_str)
        validate_workflow(workflow_def)
        # Verify DAG properties to catch cyclic dependencies early
        WorkflowDAG(workflow_def)
        
        workflow_id = uuid.uuid4().hex[:8]
        
        status = WorkflowStatus(
            workflow_id=workflow_id,
            name=workflow_def.name,
            state=WorkflowState.PENDING
        )
        
        workflows[workflow_id] = status
        workflow_definitions[workflow_id] = workflow_def
        
        return {"workflow_id": workflow_id, "status": status}
    except HTTPException:
        raise
    except (WorkflowParseError, WorkflowValidationError, CyclicDependencyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows")
def list_workflows():
    return list(workflows.values())

@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflows[workflow_id]

def execute_workflow_bg(workflow_def: WorkflowDefinition, workflow_id: str):
    try:
        scheduler = DAGScheduler()
        result_status = scheduler.execute_workflow(workflow_def, workflow_id)
        workflows[workflow_id] = result_status
    except Exception as e:
        logger.error(f"Error in background execution for workflow {workflow_id}: {e}")
        workflows[workflow_id].state = WorkflowState.FAILED
        workflows[workflow_id].error = str(e)

@app.post("/workflows/{workflow_id}/run", response_model=RunResponse)
def run_workflow(workflow_id: str):
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    status = workflows[workflow_id]
    if status.state in (WorkflowState.RUNNING, WorkflowState.COMPLETED):
        raise HTTPException(status_code=400, detail=f"Workflow already in state: {status.state}")
        
    workflow_def = workflow_definitions[workflow_id]
    
    thread = threading.Thread(
        target=execute_workflow_bg, 
        args=(workflow_def, workflow_id),
        daemon=True
    )
    thread.start()
    
    return RunResponse(
        message="Workflow execution started",
        workflow_id=workflow_id
    )

@app.get("/workflows/{workflow_id}/stages/{stage_id}/logs", response_class=PlainTextResponse)
def get_stage_logs(workflow_id: str, stage_id: str):
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    status = workflows[workflow_id]
    if stage_id not in status.stages:
        raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found in workflow")
        
    job_name = status.stages[stage_id].job_name
    if not job_name:
        raise HTTPException(status_code=400, detail="Job has not been created yet for this stage")
        
    manager = JobManager()
    logs = manager.get_job_logs(job_name)
    return logs

<<<<<<< HEAD

@app.post("/predict/stage")
def predict_stage_endpoint(stage_input: dict = Body(...)):
    try:
        predictor = get_predictor()
        return predictor.predict_stage(stage_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/workflows/{workflow_id}/predict")
def predict_workflow_endpoint(workflow_id: str, workload_metadata: Optional[dict] = Body(default=None)):
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        predictor = get_predictor()
        wf_def = workflow_definitions[workflow_id]
        return predictor.predict_workflow(wf_def, workload_metadata=workload_metadata)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/models/evaluation")
def get_models_evaluation():
    predictor = get_predictor()
    return predictor.evaluation_summary_


=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "serve":
            import uvicorn
            uvicorn.run(app, host=API_HOST, port=API_PORT)
        elif command == "run" and len(sys.argv) > 2:
            # Direct CLI execution
            file_path = sys.argv[2]
            try:
                workflow_def = parse_workflow_file(file_path)
                validate_workflow(workflow_def)
                dag = WorkflowDAG(workflow_def)
                workflow_id = uuid.uuid4().hex[:8]
                logger.info(f"[CloudPilot] Workflow submitted: {workflow_def.name} (id: {workflow_id})")
                scheduler = DAGScheduler()
                result = scheduler.execute_workflow(workflow_def, workflow_id)
                # Print final status
                print(json.dumps(result.model_dump(mode='json'), indent=2, default=str))
            except (WorkflowParseError, WorkflowValidationError, CyclicDependencyError) as e:
                logger.error(f"[CloudPilot] Error: {e}")
                sys.exit(1)
        elif command == "validate" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            try:
                workflow_def = parse_workflow_file(file_path)
                validate_workflow(workflow_def)
                dag = WorkflowDAG(workflow_def)
                print(f"Workflow '{workflow_def.name}' is valid")
                print(f"Stages: {dag.get_all_stages()}")
                print(f"Topological order: {dag.topological_order()}")
                print(f"Parallel groups: {dag.get_parallel_groups()}")
            except (WorkflowParseError, WorkflowValidationError, CyclicDependencyError) as e:
                logger.error(f"[CloudPilot] Validation failed: {e}")
                sys.exit(1)
<<<<<<< HEAD
        elif command == "predict" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            try:
                workflow_def = parse_workflow_file(file_path)
                validate_workflow(workflow_def)
                predictor = get_predictor()
                pred_res = predictor.predict_workflow(workflow_def)
                print(json.dumps(pred_res, indent=2))
            except Exception as e:
                logger.error(f"[CloudPilot] Prediction failed: {e}")
                sys.exit(1)
        else:
            print("Usage: python main.py [serve|run <workflow.yaml>|validate <workflow.yaml>|predict <workflow.yaml>]")
    else:
        print("Usage: python main.py [serve|run <workflow.yaml>|validate <workflow.yaml>|predict <workflow.yaml>]")

=======
        else:
            print("Usage: python main.py [serve|run <workflow.yaml>|validate <workflow.yaml>]")
    else:
        print("Usage: python main.py [serve|run <workflow.yaml>|validate <workflow.yaml>]")
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

