import requests
import json
import uuid
import websocket
import os
import logging
from typing import Optional, Dict, Any, List
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse
from pathlib import Path

from .workflow import Workflow
from . import utils
from .exceptions import ComfyAPIError, WorkflowError, MissingModelError

from huggingface_hub import hf_hub_download

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Base de données et configurations (inchangées) ---
KNOWN_MODELS_DB = {
    "checkpoints": {
        "v1-5-pruned-emaonly-fp16.safetensors": ("Comfy-Org/stable-diffusion-v1-5-archive", "v1-5-pruned-emaonly-fp16.safetensors"),
        "sd_xl_base_1.0.safetensors": ("stabilityai/stable-diffusion-xl-base-1.0", "sd_xl_base_1.0.safetensors"),
        "flux1-schnell-fp8.safetensors": ("Comfy-Org/flux1-schnell", "flux1-schnell-fp8.safetensors"),
        "flux1-dev-fp8.safetensors": ("Comfy-Org/flux1-dev", "flux1-dev-fp8.safetensors"),
        "sd3.5_large_fp8_scaled.safetensors": ("Comfy-Org/stable-diffusion-3.5-fp8", "sd3.5_large_fp8_scaled.safetensors")
    },
    "loras": {}, "vae": {}
}
PRESET_CONFIGS = {
    "sd15": {"checkpoint_name": "v1-5-pruned-emaonly-fp16.safetensors", "steps": 20, "cfg": 7.0, "sampler_name": "euler"},
    "sd3": {"checkpoint_name": "sd3.5_large_fp8_scaled.safetensors", "steps": 28, "cfg": 4.5, "sampler_name": "euler"},
    "flux_schnell": {"checkpoint_name": "flux1-schnell-fp8.safetensors", "steps": 8, "cfg": 1.0, "sampler_name": "euler"},
    "flux_dev": {"checkpoint_name": "flux1-dev-fp8.safetensors", "steps": 28, "cfg": 2.0, "sampler_name": "euler"}
}
MODEL_LOADER_MAP = {
    'CheckpointLoaderSimple': ('checkpoints', 'ckpt_name'),
    'LoraLoader': ('loras', 'lora_name'),
    'VAELoader': ('vae', 'vae_name'),
}

class ComfyAPI:
    def __init__(self, server_address: str, session_id: Optional[str] = None, comfyui_path: Optional[str] = None):
        if "http" not in server_address: self.http_server_address = f"http://{server_address}"
        else: self.http_server_address = server_address
        parsed_url = urlparse(self.http_server_address)
        ws_scheme = 'wss' if parsed_url.scheme == 'https' else 'ws'
        self.ws_server_address = f"{ws_scheme}://{parsed_url.netloc}"
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.ws: Optional[websocket.WebSocket] = None
        
        self.comfyui_path = Path(comfyui_path) if comfyui_path else None
        if self.comfyui_path: logger.info(f"ComfyUI path set to: {self.comfyui_path}. Automatic model download is enabled.")
        else: logger.warning("ComfyUI path not provided. Automatic model download is disabled.")
            
        logger.info(f"Initialized ComfyAPI client with session ID: {self.session_id}")

    def _download_model(self, model_name: str, model_type_folder: str):
        if not self.comfyui_path: return False
        
        db_entry = KNOWN_MODELS_DB.get(model_type_folder, {}).get(model_name)
        if not db_entry:
            logger.warning(f"Model '{model_name}' is not in the known models database. Cannot download.")
            return False

        repo_id, filename_in_repo = db_entry
        target_dir = self.comfyui_path / "models" / model_type_folder
        
        logger.info(f"Attempting to download '{model_name}'...")
        logger.info(f"Source: Hugging Face Repo '{repo_id}'")
        logger.info(f"Destination: '{target_dir}'")
        
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=filename_in_repo,
                local_dir=target_dir,
                local_dir_use_symlinks=False
            )
            logger.info(f"Successfully downloaded '{model_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to download model '{model_name}': {e}")
            return False

    def _validate_and_prepare_workflow(self, workflow_dict: Dict[str, Any]):
        """Vérifie la présence des modèles localement et les télécharge si nécessaire."""
        if not self.comfyui_path:
            return

        logger.info("Validating required models against local filesystem...")
        for node_data in workflow_dict.values():
            node_class = node_data.get('class_type')
            if node_class in MODEL_LOADER_MAP:
                model_type_folder, input_name = MODEL_LOADER_MAP[node_class]
                model_name = node_data.get('inputs', {}).get(input_name)

                if not model_name: continue

                expected_path = self.comfyui_path / "models" / model_type_folder / model_name
                
                if not expected_path.exists():
                    logger.warning(f"Model file not found locally: {expected_path}")
                    if not self._download_model(model_name, model_type_folder):
                        # Le téléchargement a échoué ou n'était pas possible
                        raise MissingModelError(f"Model '{model_name}' is missing and could not be downloaded automatically.")
                    # Si le téléchargement a réussi, on continue simplement.
                    # Le serveur ComfyUI devrait pouvoir le prendre en charge.
                    logger.info(f"Model '{model_name}' downloaded. Proceeding with execution.")

    def _queue_prompt(self, workflow_dict: Dict[str, Any]) -> str:
        self._validate_and_prepare_workflow(workflow_dict)
        
        logger.info("Validation complete. Queueing workflow to ComfyUI.")
        payload = {"prompt": workflow_dict, "client_id": self.session_id}
        data = json.dumps(payload).encode('utf-8')
        req = requests.post(f"{self.http_server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
        req.raise_for_status()
        return req.json()['prompt_id']

    # --- Le reste de la classe (text_to_image, presets, etc.) reste INCHANGÉ ---
    # La structure est déjà correcte et appelle _queue_prompt au bon moment.
    def load_workflow(self, workflow_path: str) -> 'Workflow':
        final_path = workflow_path
        if not os.path.exists(final_path):
            template_path = os.path.join(os.path.dirname(__file__), 'templates', f"{workflow_path}.json")
            if os.path.exists(template_path): final_path = template_path
            else: raise FileNotFoundError(f"Workflow file or template '{workflow_path}' not found.")
        with open(final_path, 'r', encoding='utf-8') as f:
            return Workflow(client=self, workflow_data=json.load(f))

    def text_to_image(self, positive_prompt: str, **kwargs) -> List[Image.Image]:
        logger.info("Executing generic text-to-image.")
        workflow = self.load_workflow('default_text_to_image')
        
        exec_overrides = {"positive_prompt": positive_prompt, **kwargs}
        if "checkpoint_name" in kwargs:
            ckpt_nodes = workflow.get_nodes_by_class('CheckpointLoaderSimple')
            if ckpt_nodes: workflow.set_node(ckpt_nodes[0], {"ckpt_name": kwargs["checkpoint_name"]})
        
        sampler_nodes = workflow.get_nodes_by_class('KSampler')
        if sampler_nodes:
            sampler_params = {k: v for k, v in kwargs.items() if k in ['steps', 'cfg', 'sampler_name']}
            if sampler_params: workflow.set_node(sampler_nodes[0], sampler_params)
            
        latent_nodes = workflow.get_nodes_by_class('EmptyLatentImage')
        if latent_nodes:
            latent_params = {k: v for k, v in kwargs.items() if k in ['width', 'height']}
            if latent_params: workflow.set_node(latent_nodes[0], latent_params)
            
        return workflow.execute(**exec_overrides)

    def _execute_preset(self, preset_name: str, positive_prompt: str, **kwargs) -> List[Image.Image]:
        config = PRESET_CONFIGS[preset_name]
        logger.info(f"Executing '{preset_name}' preset text-to-image.")
        final_params = {**config, **kwargs, "positive_prompt": positive_prompt}
        return self.text_to_image(**final_params)

    def text_to_image_sd15(self, *args, **kwargs): return self._execute_preset("sd15", *args, **kwargs)
    def text_to_image_sd3(self, *args, **kwargs): return self._execute_preset("sd3", *args, **kwargs)
    def text_to_image_flux_schnell(self, *args, **kwargs): return self._execute_preset("flux_schnell", *args, **kwargs)
    def text_to_image_flux_dev(self, *args, **kwargs): return self._execute_preset("flux_dev", *args, **kwargs)

    def __enter__(self): self.connect(); return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()
    def connect(self):
        if self.ws and self.ws.connected: return
        ws_url = f"{self.ws_server_address}/ws?clientId={self.session_id}"
        try:
            self.ws = websocket.WebSocket()
            self.ws.connect(ws_url)
            logger.info("WebSocket connection established.")
        except websocket.WebSocketException as e:
            raise ComfyAPIError(f"Failed to connect to WebSocket: {e}")
    def close(self): 
        if self.ws and self.ws.connected: self.ws.close(); logger.info("WebSocket connection closed.")
        self.ws = None
    
    def _handle_execution_error(self, error_data: Dict[str, Any], workflow_config: Dict[str, Any]):
        node_id, node_type, exc_message = error_data.get('node_id'), error_data.get('node_type'), error_data.get('exception_message', '')
        raise ComfyAPIError(f"Execution failed on node {node_id} ({node_type}): {exc_message}")

    def _get_images_from_ws(self, prompt_id: str, workflow_config: Dict[str, Any]) -> List[Image.Image]:
        if not self.ws or not self.ws.connected:
            raise ComfyAPIError("WebSocket is not connected. Call connect() before executing workflows.")
        results = utils.get_images_from_websocket(self.ws, prompt_id)
        if not results: return []
        if "error" in results[0]:
            self._handle_execution_error(results[0]["error"], workflow_config)
            return []
        images = []
        for img_data in results:
            if 'filename' in img_data and 'subfolder' in img_data and 'type' in img_data:
                images.append(self._get_image_file(
                    filename=img_data['filename'],
                    subfolder=img_data['subfolder'],
                    folder_type=img_data['type']
                ))
            else:
                logger.warning(f"Données d'image incomplètes reçues, ignorées : {img_data}")
        return images

    def _get_image_file(self, filename: str, subfolder: str, folder_type: str) -> Image.Image:
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        response = requests.get(f"{self.http_server_address}/view", params=params)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))