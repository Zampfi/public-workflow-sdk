"""
Workflow models for ActionsHub - independent of Pantheon platform.
"""

from pydantic import BaseModel
from typing import Callable, Any
import inspect


class Workflow(BaseModel):
    name: str
    description: str
    labels: list[str]
    class_type: type
    func: Callable | None = None
    _parameters: tuple | None = None
    _returns: type | None = None

    @property
    def parameters(self) -> tuple:
        if self._parameters is None:
            self._parameters = self._get_parameters()
        return self._parameters

    def _get_parameters(self) -> tuple:
        parameters = inspect.signature(self.func).parameters
        parameters_tuple = []
        for param_name, param in parameters.items():
            if param.name == "self":
                continue

            if param.annotation == inspect.Signature.empty:
                raise ValueError(f"Parameter {param_name} has no type annotation")
            parameters_tuple.append(param.annotation)

        return tuple(parameters_tuple)

    @property
    def returns(self) -> Any:
        if self._returns is None:
            self._returns = self._get_returns()
        return self._returns

    def _get_returns(self) -> type:
        return inspect.signature(self.func).return_annotation


class WorkflowParams(BaseModel):
    workflow_name: str
    result_type: type | None = None
    args: tuple
    kwargs: dict | None = None


class WorkflowCoordinates(BaseModel):
    workflow_name: str
    absolute_file_path: str
    relative_file_path: str
    line_number: int
    module: str
    class_name: str | None = None


# Constants
PLATFORM_WORKFLOW_LABEL = "platform"
