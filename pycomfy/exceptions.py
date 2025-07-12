class ComfyError(Exception):
    """Base exception class for all pycomfy errors."""
    pass

class ComfyAPIError(ComfyError):
    """Raised for errors related to the ComfyUI API communication."""
    pass

class WorkflowError(ComfyError):
    """Raised for errors related to workflow parsing or manipulation."""
    pass

class MissingModelError(WorkflowError):
    """Raised when a workflow execution fails due to a missing model file."""
    pass