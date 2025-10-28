import pytest

from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.list_transformer import ListTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.tuple_transformer import (
    TupleTransformer,
)
from zamp_public_workflow_sdk.temporal.data_converters.transformers.datetime_transformer import DateTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_model_metaclass_transformer import (
    PydanticModelMetaclassTransformer,
)
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_transformer import (
    PydanticTypeTransformer,
)
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.union_transformer import UnionTransformer


@pytest.fixture(scope="session", autouse=True)
def register_transformers():
    """Register all transformers before running tests."""
    # Clear any existing transformers
    Transformer._transformers = []
    Transformer._collection_transformers = []

    # Register transformers
    Transformer.register_transformer(PydanticTypeTransformer())
    Transformer.register_transformer(PydanticModelMetaclassTransformer())
    Transformer.register_transformer(BytesTransformer())
    Transformer.register_transformer(BytesIOTransformer())
    Transformer.register_transformer(DateTransformer())
    Transformer.register_transformer(UnionTransformer())

    # Register collection transformers
    Transformer.register_collection_transformer(TupleTransformer())
    Transformer.register_collection_transformer(ListTransformer())

    yield

    # Clean up after tests
    Transformer._transformers = []
    Transformer._collection_transformers = []
