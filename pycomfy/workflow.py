import json
import copy
import logging
from typing import Any, Dict, List, Optional
from PIL.Image import Image

from .exceptions import WorkflowError

class ComfyAPI:
    pass

logger = logging.getLogger(__name__)

class WorkflowNode:
    def __init__(self, node_id: str, class_type: str, title: Optional[str]):
        self.id = node_id
        self.class_type = class_type
        self.title = title

    def __repr__(self):
        return f"WorkflowNode(id='{self.id}', class_type='{self.class_type}')"

class Workflow:
    def __init__(self, client: 'ComfyAPI', workflow_data: Dict[str, Any]):
        if not isinstance(workflow_data, dict) or not all(isinstance(k, str) for k in workflow_data.keys()):
             raise WorkflowError(
                "Invalid workflow format. Expected a dictionary of node IDs (strings). "
                "Please re-save your workflow from ComfyUI using the 'Save (API Format)' button."
            )

        self._client = client
        self._original_workflow = workflow_data
        self._current_config = copy.deepcopy(self._original_workflow)
        self._execution_order: List[str] = []
        self._node_map: Dict[str, WorkflowNode] = {}
        self._class_type_map: Dict[str, List[WorkflowNode]] = {}
        self._analyze_workflow()

    def _analyze_workflow(self):
        # ... (Cette méthode reste identique à la version précédente)
        all_node_ids = set(self._original_workflow.keys())
        input_sources = set()
        for node_data in self._original_workflow.values():
            for input_value in node_data.get('inputs', {}).values():
                if isinstance(input_value, list) and len(input_value) == 2 and isinstance(input_value[0], str):
                    input_sources.add(input_value[0])
        output_node_ids = all_node_ids - input_sources
        nodes_to_visit = list(output_node_ids)
        visited = set()
        while nodes_to_visit:
            node_id = nodes_to_visit.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            self._execution_order.insert(0, node_id)
            node_data = self._original_workflow.get(node_id, {})
            for input_value in node_data.get('inputs', {}).values():
                if isinstance(input_value, list) and len(input_value) == 2 and isinstance(input_value[0], str):
                    nodes_to_visit.append(input_value[0])
        for node_id in self._execution_order:
            node_data = self._original_workflow[node_id]
            class_type = node_data['class_type']
            title = node_data.get('_meta', {}).get('title')
            node_obj = WorkflowNode(node_id, class_type, title)
            self._node_map[node_id] = node_obj
            if class_type not in self._class_type_map:
                self._class_type_map[class_type] = []
            self._class_type_map[class_type].append(node_obj)

    def _find_node_by_role(self, role: str) -> Optional[WorkflowNode]:
        # ... (Cette méthode reste identique)
        samplers = self.get_nodes_by_class("KSampler")
        if not samplers: return None
        main_sampler_id = samplers[0].id
        sampler_inputs = self._original_workflow[main_sampler_id]['inputs']
        input_map = {'positive_prompt': 'positive', 'negative_prompt': 'negative'}
        target_input_name = input_map.get(role)
        if not target_input_name or target_input_name not in sampler_inputs:
             return None
        source_link = sampler_inputs[target_input_name]
        if isinstance(source_link, list):
            source_node_id = source_link[0]
            return self._node_map.get(source_node_id)
        return None

    def _update_node_input(self, config: Dict, node_id: str, input_name: str, new_value: Any):
        # ... (Cette méthode reste identique)
        node = config.get(node_id, {})
        if "inputs" not in node:
            node["inputs"] = {}
        node["inputs"][input_name] = new_value
        logger.debug(f"Updated node '{node_id}' input '{input_name}' to: {new_value}")

    def _apply_config(self, config: Dict, **kwargs):
        """Applies configuration from kwargs, supporting only basic, universal shortcuts."""
        for key, value in kwargs.items():
            if key in ['positive_prompt', 'negative_prompt']:
                node_to_update = self._find_node_by_role(key)
                if node_to_update:
                    self._update_node_input(config, node_to_update.id, "text", value)
            elif key == 'seed':
                for sampler in self.get_nodes_by_class("KSampler"):
                    self._update_node_input(config, sampler.id, "seed", value)
            else:
                logger.warning(f"Argument '{key}' non reconnu comme raccourci universel. Utilisez workflow.set_node() pour des modifications spécifiques.")

    def get_nodes_by_class(self, class_type: str) -> List[WorkflowNode]:
        """Returns all nodes of a specific class type, in execution order."""
        return self._class_type_map.get(class_type, [])

    def set_node(self, node: WorkflowNode, params: Dict[str, Any]):
        """Persistently sets input parameters for a specific node."""
        if not isinstance(node, WorkflowNode) or node.id not in self._node_map:
            raise WorkflowError("Invalid node object provided.")
        logger.info(f"Setting persistent config for node {node.id}: {params}")
        for param, value in params.items():
            self._update_node_input(self._current_config, node.id, param, value)

    def set(self, **kwargs):
        """Persistently sets configuration values for this workflow instance using basic shortcuts."""
        logger.info(f"Setting persistent config for workflow: {kwargs}")
        self._apply_config(self._current_config, **kwargs)

    def execute(self, **kwargs) -> List[Image]:
        """Executes the workflow and returns the final images."""
        self._client.connect()
        execution_config = copy.deepcopy(self._current_config)
        
        if kwargs:
            logger.info(f"Applying temporary overrides for execution: {kwargs}")
            self._apply_config(execution_config, **kwargs)

        prompt_to_queue = {node_id: execution_config[node_id] for node_id in self._execution_order}
        
        prompt_id = self._client._queue_prompt(prompt_to_queue)
        logger.info(f"Workflow queued with prompt ID: {prompt_id}. Waiting for results...")
        
        images = self._client._get_images_from_ws(prompt_id, execution_config)
        logger.info(f"Execution finished. Received {len(images)} image(s).")
        return images