from __future__ import annotations

from typing import Dict, TypeVar

from pydantic import BaseModel

from zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models import TestModelWithListOfIntegers
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn

T = TypeVar("T", bound=BaseModel)


def test_get_fqn():
    assert get_fqn(int) == "int"
    assert get_fqn(str) == "str"
    assert get_fqn(float) == "float"
    assert get_fqn(bool) == "bool"
    assert get_fqn(list) == "list"
    assert get_fqn(dict) == "dict"
    assert get_fqn(list[int]) == "list[int]"
    assert get_fqn(list[list[str]]) == "list[list[str]]"
    assert get_fqn(dict[str, int]) == "dict[str, int]"
    assert get_fqn(list[dict[str, int]]) == "list[dict[str, int]]"
    assert (
        get_fqn(TestModelWithListOfIntegers)
        == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithListOfIntegers"
    )
    assert get_fqn(dict[str, int]) == "typing.Dict[str, int]"


def test_get_reference_from_fqn():
    assert get_reference_from_fqn("int") == int
    assert get_reference_from_fqn("str") == str
    assert get_reference_from_fqn("float") == float
    assert get_reference_from_fqn("bool") == bool
    assert get_reference_from_fqn("list[int]") == list[int]
    assert get_reference_from_fqn("list[list[str]]") == list[list[str]]
    assert get_reference_from_fqn("dict[str, int]") == dict[str, int]
    assert get_reference_from_fqn("list[dict[str, int]]") == list[dict[str, int]]
    assert (
        get_reference_from_fqn(
            "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithListOfIntegers"
        )
        == TestModelWithListOfIntegers
    )
    assert get_reference_from_fqn("typing.Dict[str, int]") == dict[str, int]


if __name__ == "__main__":
    test_get_fqn()
    test_get_reference_from_fqn()
