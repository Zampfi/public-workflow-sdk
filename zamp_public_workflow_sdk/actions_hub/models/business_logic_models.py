"""
Business logic models for ActionsHub - independent of Pantheon platform.
"""

from pydantic import BaseModel
from typing import Callable, Any
import inspect


class BusinessLogic(BaseModel):
    name: str
    description: str
    labels: list[str]
    func: Callable
    _parameters: tuple = None
    _returns: type | None = None

    @property
    def parameters(self) -> tuple:
        if self._parameters is None:
            self._parameters = self._get_parameters()
        return self._parameters

    @property
    def returns(self) -> Any:
        if self._returns is None:
            self._returns = self._get_returns()
        return self._returns

    def _get_parameters(self) -> tuple:
        parameters = inspect.signature(self.func).parameters
        params = []
        for param_name, param in parameters.items():
            if param.name == "self":
                continue

            if param.annotation == inspect.Signature.empty:
                raise ValueError(f"Parameter {param_name} has no type annotation")

            params.append(param.annotation)
        return tuple(params)

    def _get_returns(self) -> type:
        return inspect.signature(self.func).return_annotation
