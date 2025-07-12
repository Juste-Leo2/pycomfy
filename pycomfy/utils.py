import json
import websocket
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_images_from_websocket(ws: websocket.WebSocket, prompt_id: str) -> List[Dict[str, Any]]:
    """
    Listens to the WebSocket for execution updates and returns the image data
    when a node produces an image output for our prompt.
    Also listens for execution errors.
    """
    logger.debug(f"Listening on WebSocket for prompt ID: {prompt_id}")
    ws.settimeout(240.0)

    while True:
        try:
            out = ws.recv()
            if not isinstance(out, str):
                continue

            message = json.loads(out)
            message_type = message.get('type')

            if message_type == 'execution_error':
                data = message.get('data', {})
                if data.get('prompt_id') == prompt_id:
                    logger.error("Execution error received from ComfyUI.")
                    return [{"error": data}]

            if message_type == 'executed' and message['data'].get('prompt_id') == prompt_id:
                data = message.get('data', {})
                node_outputs = data.get('output', {})

                if 'images' in node_outputs and isinstance(node_outputs['images'], list):
                    image_data_list = node_outputs['images']
                    if image_data_list:
                        logger.info(f"Found {len(image_data_list)} image(s) in node output (ID: {data.get('node')}).")
                        return image_data_list

        except websocket.WebSocketTimeoutException:
            logger.error("WebSocket connection timed out waiting for image data.")
            break
        except websocket.WebSocketConnectionClosedException:
            logger.error("WebSocket connection closed unexpectedly.")
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred in WebSocket communication: {e}")
            break
            
    logger.warning("Exiting WebSocket loop. No definitive image data or error was found for the prompt.")
    return []