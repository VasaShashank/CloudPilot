import pytest
from backend.workflow.dag import WorkflowDAG, CyclicDependencyError
from backend.models.workflow import WorkflowDefinition, StageDefinition

def test_dag_linear():
    wf = WorkflowDefinition(name="linear", stages=[
        StageDefinition(id="qc", type="Job"),
        StageDefinition(id="preprocessing", type="Job", depends_on=["qc"]),
        StageDefinition(id="alignment", type="Job", depends_on=["preprocessing"]),
        StageDefinition(id="analysis", type="Job", depends_on=["alignment"]),
    ])
    dag = WorkflowDAG(wf)
    assert dag.get_root_stages() == ["qc"]
    assert dag.topological_order() == ["qc", "preprocessing", "alignment", "analysis"]
    assert dag.get_downstream("qc") == ["preprocessing"]
    assert dag.get_dependencies("analysis") == ["alignment"]

def test_dag_parallel_branches():
    wf = WorkflowDefinition(name="diamond", stages=[
        StageDefinition(id="qc", type="Job"),
        StageDefinition(id="preprocessing", type="Job", depends_on=["qc"]),
        StageDefinition(id="alignment", type="Job", depends_on=["preprocessing"]),
        StageDefinition(id="feature_extraction", type="Job", depends_on=["preprocessing"]),
        StageDefinition(id="analysis", type="Job", depends_on=["alignment", "feature_extraction"]),
    ])
    dag = WorkflowDAG(wf)
    runnable = set(dag.get_runnable_stages({"qc", "preprocessing"}))
    assert runnable == {"alignment", "feature_extraction"}
    
    pgroups = dag.get_parallel_groups()
    # Find the group containing alignment
    alignment_group = [g for g in pgroups if "alignment" in g][0]
    assert "feature_extraction" in alignment_group

def test_dag_cycle_detection():
    wf = WorkflowDefinition(name="cycle", stages=[
        StageDefinition(id="A", type="Job", depends_on=["C"]),
        StageDefinition(id="B", type="Job", depends_on=["A"]),
        StageDefinition(id="C", type="Job", depends_on=["B"]),
    ])
    with pytest.raises(CyclicDependencyError):
        WorkflowDAG(wf)

def test_dag_runnable_stages_initial():
    wf = WorkflowDefinition(name="linear", stages=[
        StageDefinition(id="A", type="Job"),
        StageDefinition(id="B", type="Job", depends_on=["A"])
    ])
    dag = WorkflowDAG(wf)
    assert dag.get_runnable_stages(set()) == ["A"]

def test_dag_runnable_stages_progressive():
    wf = WorkflowDefinition(name="diamond", stages=[
        StageDefinition(id="qc", type="Job"),
        StageDefinition(id="preprocessing", type="Job", depends_on=["qc"]),
        StageDefinition(id="alignment", type="Job", depends_on=["preprocessing"]),
        StageDefinition(id="feature_extraction", type="Job", depends_on=["preprocessing"])
    ])
    dag = WorkflowDAG(wf)
    # After QC
    assert dag.get_runnable_stages({"qc"}) == ["preprocessing"]
    # After preprocessing
    runnable = set(dag.get_runnable_stages({"qc", "preprocessing"}))
    assert runnable == {"alignment", "feature_extraction"}

def test_dag_all_stages():
    wf = WorkflowDefinition(name="all", stages=[
        StageDefinition(id="A", type="Job"),
        StageDefinition(id="B", type="Job")
    ])
    dag = WorkflowDAG(wf)
    stages = set(dag.get_all_stages())
    assert stages == {"A", "B"}

def test_dag_stage_data():
    s = StageDefinition(id="A", type="Job", memory="1Gi")
    wf = WorkflowDefinition(name="data", stages=[s])
    dag = WorkflowDAG(wf)
    assert dag.get_stage_data("A") == s
    assert dag.get_stage_data("A").memory == "1Gi"

def test_dag_topological_order_respects_dependencies():
    wf = WorkflowDefinition(name="deps", stages=[
        StageDefinition(id="D", type="Job", depends_on=["B", "C"]),
        StageDefinition(id="B", type="Job", depends_on=["A"]),
        StageDefinition(id="C", type="Job", depends_on=["A"]),
        StageDefinition(id="A", type="Job")
    ])
    dag = WorkflowDAG(wf)
    order = dag.topological_order()
    
    assert order.index("A") < order.index("B")
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")

def test_dag_single_stage():
    wf = WorkflowDefinition(name="single", stages=[
        StageDefinition(id="A", type="Job")
    ])
    dag = WorkflowDAG(wf)
    assert dag.get_root_stages() == ["A"]
    assert dag.topological_order() == ["A"]

def test_dag_multiple_roots():
    wf = WorkflowDefinition(name="multi_roots", stages=[
        StageDefinition(id="A", type="Job"),
        StageDefinition(id="B", type="Job")
    ])
    dag = WorkflowDAG(wf)
    roots = set(dag.get_root_stages())
    assert roots == {"A", "B"}
