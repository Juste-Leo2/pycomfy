# This file makes the main classes and exceptions available.
from .client import ComfyAPI
from .workflow import Workflow
# On ajoute la nouvelle exception à l'importation
from .exceptions import ComfyAPIError, WorkflowError, ComfyError, MissingModelError

# This defines what `from pycomfy import *` will import.
# On ajoute aussi la nouvelle exception à la liste __all__
__all__ = ["ComfyAPI", "Workflow", "ComfyAPIError", "WorkflowError", "ComfyError", "MissingModelError"]