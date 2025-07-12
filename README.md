# pycomfy - A simple and robust Python client for ComfyUI

`pycomfy` is a Python library designed to make interacting with the [ComfyUI API](https://github.com/comfyanonymous/ComfyUI) straightforward and developer-friendly. It handles complex tasks like workflow management and model downloading automatically, allowing you to focus on generating images.

## Features

- **Automatic Model Downloading**: If a required model (checkpoint) is missing, `pycomfy` will automatically download it from Hugging Face if you provide your local ComfyUI path.
- **High-Level Presets**: Generate images with popular models like SD1.5, SD3, and FLUX using simple, one-line functions (e.g., `api.text_to_image_sd15(...)`).
- **Full Customization**: A generic `api.text_to_image(...)` function gives you full control over every parameter.
- **Expert Workflow Control**: Load, inspect, and modify any custom ComfyUI workflow directly from your Python code.
- **Zero-Fuss Experience**: No need to restart the ComfyUI server after a model is downloaded. The library handles it, and your script continues seamlessly.

## Installation

```
pip install pycomfy
```

## Getting Started: The Simple Way

This is the easiest way to start generating images. The library takes care of everything.

1.  **Provide your ComfyUI path**: This is optional, but **required** to enable automatic model downloading.
2.  **Call a preset function**: Choose a model and provide your prompts.

```python
from pycomfy import ComfyAPI, MissingModelError

# This is optional, but required for the automatic download feature.
# Replace with your actual path to the main ComfyUI folder.
COMFYUI_PATH = "C:/path/to/your/ComfyUI"

try:
    # Initialize the API
    api = ComfyAPI("127.0.0.1:8188", comfyui_path=COMFYUI_PATH)

    # Generate an image using a high-level preset
    # If the model is missing, it will be downloaded automatically.
    print("Generating with the SD1.5 preset...")
    images = api.text_to_image_sd15(
        positive_prompt="a majestic lion on a throne, cinematic lighting, highly detailed",
        negative_prompt="blurry, cartoon, bad art",
        seed=42
    )

    if images:
        images[0].save("lion_king.png")
        print("Image 'lion_king.png' saved successfully!")

except MissingModelError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

## Usage

### 1. Initialization

```python
from pycomfy import ComfyAPI

# Basic initialization (automatic download disabled)
api = ComfyAPI("127.0.0.1:8188")

# Initialization with automatic download enabled
api = ComfyAPI("127.0.0.1:8188", comfyui_path="C:/path/to/your/ComfyUI")
```

### 2. Preset Functions

These are shortcuts for common text-to-image tasks. They use pre-configured settings that you can easily override.

```python
# Stable Diffusion 1.5
images = api.text_to_image_sd15(positive_prompt="an astronaut riding a horse")

# Stable Diffusion 3
images = api.text_to_image_sd3(positive_prompt="an astronaut riding a horse")

# FLUX.1 Schnell
images = api.text_to_image_flux_schnell(positive_prompt="an astronaut riding a horse")

# FLUX.1 Dev
images = api.text_to_image_flux_dev(positive_prompt="an astronaut riding a horse")

# You can also override any parameter
images = api.text_to_image_flux_schnell(
    positive_prompt="an astronaut riding a horse",
    steps=10, # Default is 8 for this preset
    seed=12345
)
```

### 3. Generic Text-to-Image Function

For full control when presets are not enough. Specify any parameter you need.

```python
images = api.text_to_image(
    positive_prompt="a cute cat programmer, 8k, highest quality",
    negative_prompt="bad anatomy, watermark, blurry",
    checkpoint_name="v1-5-pruned-emaonly-fp16.safetensors",
    steps=25,
    cfg=8.0,
    sampler_name="dpmpp_2m_karras",
    width=768,
    height=512,
    seed=9876
)
```

### 4. The Expert Way: Custom Workflows

For maximum flexibility, you can load a custom workflow JSON file (saved from ComfyUI with "Save (API Format)") and manipulate its nodes.

```python
# 1. Load your custom workflow
workflow = api.load_workflow("my_special_workflow_api.json")

# 2. Find the nodes you want to change
sampler_nodes = workflow.get_nodes_by_class("KSampler")
checkpoint_nodes = workflow.get_nodes_by_class("CheckpointLoaderSimple")

# 3. Set new values for the nodes
if checkpoint_nodes:
    workflow.set_node(checkpoint_nodes[0], {"ckpt_name": "sd_xl_base_1.0.safetensors"})

if sampler_nodes:
    workflow.set_node(sampler_nodes[0], {"steps": 30, "cfg": 8.5})

# 4. Execute the workflow with dynamic prompts
images = workflow.execute(
    positive_prompt="a beautiful landscape, matte painting, trending on artstation",
    negative_prompt="ugly, jpeg artifacts",
    seed=42
)

if images:
    images[0].save("expert_mode_image.png")
```

## Error Handling

The library uses custom exceptions to help you debug. The most common one is `MissingModelError`, which is raised if a model file is missing and could not be downloaded automatically (e.g., it's not in the known model database).

## License

This project is licensed under the MIT License.