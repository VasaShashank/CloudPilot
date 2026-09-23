import networkx as nx
import logging
from backend.models.workflow import WorkflowDefinition, StageDefinition

logger = logging.getLogger('cloudpilot')

class CyclicDependencyError(Exception):
    pass

class WorkflowDAG:
    def __init__(self, workflow: WorkflowDefinition):
        self.graph = nx.DiGraph()
        self.stage_data = {}
        
        for stage in workflow.stages:
            self.graph.add_node(stage.id, data=stage)
            self.stage_data[stage.id] = stage
            
        for stage in workflow.stages:
            for dep in stage.depends_on:
                self.graph.add_edge(dep, stage.id)
                
        if not nx.is_directed_acyclic_graph(self.graph):
            cycle = nx.find_cycle(self.graph)
            raise CyclicDependencyError(f"Cycle detected in workflow dependencies: {cycle}")
            
    def get_root_stages(self) -> list[str]:
        return [n for n, d in self.graph.in_degree() if d == 0]
        
    def get_dependencies(self, stage_id: str) -> list[str]:
        return list(self.graph.predecessors(stage_id))
        
    def get_downstream(self, stage_id: str) -> list[str]:
        return list(self.graph.successors(stage_id))
        
    def get_runnable_stages(self, completed: set[str]) -> list[str]:
        runnable = []
        for node in self.graph.nodes():
            if node not in completed:
                preds = self.get_dependencies(node)
                if all(p in completed for p in preds):
                    runnable.append(node)
        return runnable
        
    def topological_order(self) -> list[str]:
        return list(nx.topological_sort(self.graph))
        
    def get_parallel_groups(self) -> list[list[str]]:
        groups = []
        in_degrees = dict(self.graph.in_degree())
        while in_degrees:
            group = [node for node, degree in in_degrees.items() if degree == 0]
            if not group:
                break
            groups.append(group)
            for node in group:
                del in_degrees[node]
                for successor in self.graph.successors(node):
                    in_degrees[successor] -= 1
        return groups
        
    def get_all_stages(self) -> list[str]:
        return list(self.graph.nodes())
        
    def get_stage_data(self, stage_id: str) -> StageDefinition:
        return self.stage_data[stage_id]
