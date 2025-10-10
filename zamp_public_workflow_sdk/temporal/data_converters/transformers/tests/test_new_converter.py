from __future__ import annotations

import io
from typing import Generic, TypeVar

from pydantic import BaseModel

from zamp_public_workflow_sdk.temporal.data_converters.type_utils import is_serialize_by_default_serializer

# Define TypeVar for generic types
T = TypeVar("T", bound=BaseModel)


def test_simple_pydantic_model():
    class SimplePydanticModel(BaseModel):
        string: str
        integer: int
        boolean: bool

    test = SimplePydanticModel(string="a", integer=1, boolean=False)

    assert is_serialize_by_default_serializer(test) is True


def test_pydantic_model_with_bytesio():
    class PydanticModelWithBytesIO(BaseModel):
        base_io: io.BytesIO

        class Config:
            arbitrary_types_allowed = True

    test = PydanticModelWithBytesIO(base_io=io.BytesIO(b"test"))

    assert is_serialize_by_default_serializer(test) is False


def test_pydantic_model_with_type_property():
    class PydanticModelWithTypeProperty(BaseModel):
        type_prop: type[BaseModel]

    test = PydanticModelWithTypeProperty(
        type_prop=PydanticModelWithTypeProperty,
    )

    assert is_serialize_by_default_serializer(test) is False


def test_pydantic_model_with_pydantic_object():
    class PydanticModelWithTypeProperty(BaseModel):
        optional_base_model: BaseModel | None

    test = PydanticModelWithTypeProperty(
        optional_base_model=PydanticModelWithTypeProperty(
            optional_base_model=None,
        ),
    )

    assert is_serialize_by_default_serializer(test) is False


def test_pydantic_model_with_pydantic_object2():
    class PydanticModelWithTypeProperty(BaseModel):
        optional_type_base_model: BaseModel | None

    test = PydanticModelWithTypeProperty(
        optional_base_model=PydanticModelWithTypeProperty(
            optional_type_base_model=PydanticModelWithTypeProperty(optional_type_base_model=None)
        ),
        optional_type_base_model=None,
    )

    assert is_serialize_by_default_serializer(test) is False


def test_nested_base_model():
    class BasicPydanticObject(BaseModel):
        string: str
        integer: int

    class PydanticModelWithNonSerializable(BaseModel):
        bytes_io: io.BytesIO

        class Config:
            arbitrary_types_allowed = True

    class NestedPydanticModel(BaseModel):
        basic: BasicPydanticObject
        non_serializable: PydanticModelWithNonSerializable | None

    nested_model = NestedPydanticModel(
        basic=BasicPydanticObject(
            string="test",
            integer=123,
        ),
        non_serializable=PydanticModelWithNonSerializable(bytes_io=io.BytesIO(b"test")),
    )

    assert is_serialize_by_default_serializer(nested_model) is False
    nested_model_dumped = {
        "basic": {"string": "test"},
        "non_serializable": io.BytesIO(b"test"),
    }
    assert is_serialize_by_default_serializer(nested_model_dumped) is False

    nested_model.non_serializable = None
    assert is_serialize_by_default_serializer(nested_model) is True
    nested_model_dumped = nested_model_dumped = {
        "basic": {"string": "test"},
        "non_serializable": None,
    }
    assert is_serialize_by_default_serializer(nested_model_dumped) is True


def test_tuple_case():
    class PydanticModelWithTuple(BaseModel):
        tuple: tuple

    test = PydanticModelWithTuple(tuple=(1, 2, 3))

    assert is_serialize_by_default_serializer(test) is False


def test_list_case():
    class PydanticModelWithList(BaseModel):
        list: list[int]

    class PydanticModelWithListT(BaseModel, Generic[T]):
        list: list[T]

    class PydanticModelWithListT2(BaseModel):
        list: list

    test1 = PydanticModelWithList(list=[1, 2, 3])

    test = PydanticModelWithListT[PydanticModelWithList](list=[test1, test1])

    test2 = PydanticModelWithListT2(list=[1, "a", 3])

    assert is_serialize_by_default_serializer(test1) is True
    assert is_serialize_by_default_serializer(test) is False
    assert is_serialize_by_default_serializer(test2) is False


if __name__ == "__main__":
    test_simple_pydantic_model()
    test_pydantic_model_with_bytesio()
    test_pydantic_model_with_type_property()
    test_pydantic_model_with_pydantic_object()
    test_pydantic_model_with_pydantic_object2()
    test_nested_base_model()
    test_tuple_case()
    test_list_case()
